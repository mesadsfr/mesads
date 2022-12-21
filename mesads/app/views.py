import collections
import csv
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.exceptions import SuspiciousOperation
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.db.models import Count, Q, Value
from django.db.models.functions import Replace
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.urls import reverse, reverse_lazy
from django.views.generic import UpdateView, TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, DeleteView, FormView, ProcessFormView
from django.views.generic.list import ListView

from reversion.views import RevisionMixin

from mesads.fradm.models import EPCI

from .forms import (
    ADSLegalFileFormSet,
    ADSManagerForm,
    ADSManagerEditForm,
    ADSSearchForm,
    ADSUserFormSet,
    ADSForm,
)
from .models import (
    ADS,
    ADSManager,
    ADSManagerAdministrator,
    ADSManagerRequest,
    ADSUser,
)


class HTTP500View(TemplateView):
    """The default HTTP/500 handler can't access to context processors and does
    not have access to the variable MESADS_CONTACT_EMAIL.
    """
    template_name = '500.html'


class HomepageView(TemplateView):
    """Render template when user is not connected. If user is connected,
    redirect depending on permissions."""
    template_name = 'pages/homepage.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_staff:
            return redirect(reverse('app.dashboards.list'))
        if len(self.request.user.adsmanageradministrator_set.all()):
            return redirect(reverse('app.ads-manager-admin.index'))
        return redirect(reverse('app.ads-manager.index'))


class ADSManagerAdminView(RevisionMixin, TemplateView):
    template_name = 'pages/ads_manager_admin.html'

    def get_context_data(self, **kwargs):
        """Populate context with the list of ADSManagerRequest current user can accept.
        """
        ctx = super().get_context_data(**kwargs)
        ctx['ads_manager_requests'] = ADSManagerRequest.objects.select_related(
            'ads_manager__administrator',
            'ads_manager__administrator__prefecture',
            'ads_manager__content_type',
            'user',
        ).prefetch_related(
            'ads_manager__content_object'
        ).filter(
            ads_manager__administrator__users__in=[self.request.user]
        ).order_by('ads_manager__administrator', '-created_at')
        return ctx

    def post(self, request):
        request_id = request.POST.get('request_id')
        action = request.POST.get('action')

        if action not in ('accept', 'deny'):
            raise SuspiciousOperation('Invalid action')

        ads_manager_request = get_object_or_404(
            ADSManagerRequest,
            id=request_id
        )

        # Make sure current user can accept this request
        get_object_or_404(
            ADSManagerAdministrator,
            users__in=[request.user],
            adsmanager=ads_manager_request.ads_manager
        )

        if action == 'accept':
            ads_manager_request.accepted = True
        else:
            ads_manager_request.accepted = False
        ads_manager_request.save()

        # Send notification to user
        email_subject = render_to_string(
            'pages/email_ads_manager_request_result_subject.txt', {
                'ads_manager_request': ads_manager_request,
            }
        ).strip()
        email_content = render_to_string(
            'pages/email_ads_manager_request_result_content.txt', {
                'request': request,
                'ads_manager_request': ads_manager_request,
                'MESADS_CONTACT_EMAIL': settings.MESADS_CONTACT_EMAIL,
            }
        )
        send_mail(
            email_subject,
            email_content,
            settings.MESADS_CONTACT_EMAIL,
            [ads_manager_request.user.email],
            fail_silently=True,
        )
        return redirect(reverse('app.ads-manager-admin.index'))


class ADSManagerRequestView(FormView):
    template_name = 'pages/ads_manager_request.html'
    form_class = ADSManagerForm
    success_url = reverse_lazy('app.ads-manager.index')

    def get_context_data(self, **kwargs):
        """Expose the list of ADSManagerAdministrators for which current user
        is configured.

        It is also accessible through user.adsmanageradministrator_set.all, but
        we need to prefetch ads_managers__content_object to reduce the number
        of SQL queries generated.
        """
        ctx = super().get_context_data(**kwargs)
        ctx['user_ads_manager_requests'] = ADSManagerRequest.objects \
            .filter(user=self.request.user) \
            .annotate(ads_count=Count('ads_manager__ads')) \
            .all()

        ctx['ads_managers_administrators'] = ADSManagerAdministrator.objects.select_related(
            'prefecture'
        ).prefetch_related(
            'adsmanager_set__content_object',
            'adsmanager_set__ads_set',
        ).filter(
            users=self.request.user
        ).all()
        return ctx

    def form_valid(self, form):
        _, created = ADSManagerRequest.objects.get_or_create(
            user=self.request.user,
            ads_manager=form.cleaned_data['ads_manager'],
        )

        # Request already exists
        if not created:
            messages.warning(
                self.request,
                self.get_message_for_existing_request(form.cleaned_data['ads_manager'])
            )
        # Send notifications to administrators.
        else:
            messages.success(
                self.request,
                self.get_message_for_new_request(form.cleaned_data['ads_manager'])
            )
            email_subject = render_to_string(
                'pages/email_ads_manager_request_administrator_subject.txt', {
                    'user': self.request.user,
                }
            ).strip()
            email_content = render_to_string(
                'pages/email_ads_manager_request_administrator_content.txt', {
                    'request': self.request,
                    'ads_manager': form.cleaned_data['ads_manager'],
                    'user': self.request.user,
                }
            )

            if form.cleaned_data['ads_manager'].administrator:
                for administrator_user in form.cleaned_data['ads_manager'].administrator.users.all():
                    send_mail(
                        email_subject,
                        email_content,
                        settings.MESADS_CONTACT_EMAIL,
                        [administrator_user],
                        fail_silently=True,
                    )

        return super().form_valid(form)

    def get_message_for_existing_request(self, ads_manager):
        if not ads_manager.administrator:
            return '''
                Vous avez déjà effectué une demande pour gérer les ADS de %(administration)s, et notre équipe va y répondre dans les plus brefs délais.<br /><br />

                Si vous n'avez eu aucun retour depuis plusieurs jours, n'hésitez pas à contacter notre équipe par email à <a href="mailto:%(email)s">%(email)s</a> ou via notre module de tchat.
            ''' % {
                'email': settings.MESADS_CONTACT_EMAIL,
                'administration': ads_manager.content_object.display_fulltext(),
            }
        return '''
            Vous avez déjà effectué une demande pour gérer les ADS de %(administration)s. Cette demande a été envoyée à %(prefecture)s qui devrait y répondre rapidement.<br /><br />

            Si vous n'avez eu aucun retour depuis plusieurs jours, n'hésitez pas à nous signaler le problème par email à <a href="mailto:%(email)s">%(email)s</a> ou via notre module de tchat.
            <br /><br />
            Nous pourrons alors valider votre demande manuellement.
        ''' % {
            'administration': ads_manager.content_object.display_fulltext(),
            'prefecture': ads_manager.administrator.prefecture.display_fulltext(),
            'email': settings.MESADS_CONTACT_EMAIL,
        }

    def get_message_for_new_request(self, ads_manager):
        # Request for EPCI or prefectures
        if not ads_manager.administrator:
            return '''
                Votre demande vient d’être envoyée à notre équipe. Vous recevrez une confirmation de validation de votre
                accès par mail.<br /><br />

                En cas de difficulté ou si vous n’obtenez pas de validation de votre demande vous pouvez contacter par email à
                <a href="mailto:%(email)s">%(email)s</a> ou via notre module de tchat.<br /><br />

                Vous pouvez également demander un accès pour la gestion des ADS d’une autre collectivité.
            ''' % {
                'email': settings.MESADS_CONTACT_EMAIL
            }

        return '''
            Votre demande vient d’être envoyée à %(prefecture)s. Vous recevrez une confirmation de validation de votre
            accès par mail.<br /><br />

            En cas de difficulté ou si vous n’obtenez pas de validation de votre demande vous pouvez
            contacter par email à <a href="mailto:%(email)s">%(email)s</a> ou via notre module de tchat.<br /><br />

            Vous pouvez également demander un accès pour la gestion des ADS d’une autre collectivité.
        ''' % {
            'prefecture': ads_manager.administrator.prefecture.display_fulltext(),
            'email': settings.MESADS_CONTACT_EMAIL
        }


class ADSManagerView(ListView, ProcessFormView):
    template_name = 'pages/ads_manager.html'
    model = ADS
    paginate_by = 50

    def get_ads_manager(self):
        return ADSManager.objects.get(id=self.kwargs['manager_id'])

    def get_form(self):
        if self.request.method == 'POST':
            return ADSManagerEditForm(instance=self.get_ads_manager(), data=self.request.POST)
        return ADSManagerEditForm(instance=self.get_ads_manager())

    def form_valid(self, form):
        form.save()
        return redirect('app.ads-manager.detail', manager_id=self.kwargs['manager_id'])

    def form_invalid(self, form):
        return ListView.get(self, self.request, *self.args, **self.kwargs)

    def _get_search_form(self):
        return ADSSearchForm(self.request.GET)

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(ads_manager__id=self.kwargs['manager_id'])

        form = self._get_search_form()
        if form.is_valid():
            if form.cleaned_data['accepted_cpam'] is not None:
                qs = qs.filter(accepted_cpam=form.cleaned_data['accepted_cpam'])

            q = form.cleaned_data['q']
            if q:
                qs = qs.annotate(
                    clean_immatriculation_plate=Replace('immatriculation_plate', Value('-'), Value(''))
                )

                qs = qs.filter(
                    Q(owner_siret__icontains=q)
                    | Q(adsuser__name__icontains=q)
                    | Q(adsuser__siret__icontains=q)
                    | Q(owner_name__icontains=q)
                    | Q(clean_immatriculation_plate__icontains=q)
                )

        # Add ordering on the number. CAST is necessary in the case the ADS number is not an integer.
        qs_ordered = qs.extra(
            select={'ads_number_as_int': "CAST(substring(number FROM '^[0-9]+') AS NUMERIC)"}
        )

        # First, order by number if it is an integer, then by string.
        return qs_ordered.annotate(c=Count('id')).order_by('ads_number_as_int', 'number')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search_form'] = self._get_search_form()
        ctx['edit_form'] = self.get_form()
        ctx['ads_manager'] = ctx['edit_form'].instance
        return ctx


class ADSView(RevisionMixin, UpdateView):
    template_name = 'pages/ads.html'
    form_class = ADSForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        # For EPCI, initialize ADSForm with the parameter epci required to setup
        # autocompletion for the field ADS.epci_commune.
        ads_manager = get_object_or_404(ADSManager, id=self.kwargs['manager_id'])
        if ads_manager.content_type.model_class() is EPCI:
            kwargs['epci'] = ads_manager.content_object

        return kwargs

    def get_success_url(self):
        return reverse('app.ads.detail', kwargs={
            'manager_id': self.kwargs['manager_id'],
            'ads_id': self.kwargs['ads_id'],
        })

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['ads_manager'] = ADSManager.objects.get(id=self.kwargs['manager_id'])

        if self.request.POST:
            ctx['ads_users_formset'] = ADSUserFormSet(self.request.POST, instance=self.object)
            ctx['ads_legal_files_formset'] = ADSLegalFileFormSet(self.request.POST, self.request.FILES, instance=self.object)
        else:
            ctx['ads_users_formset'] = ADSUserFormSet(instance=self.object)
            ctx['ads_legal_files_formset'] = ADSLegalFileFormSet(instance=self.object)
        return ctx

    def get_object(self, queryset=None):
        return get_object_or_404(ADS, id=self.kwargs['ads_id'])

    def form_valid(self, form):
        ctx = self.get_context_data()
        ads_users_formset = ctx['ads_users_formset']
        ads_legal_files_formset = ctx['ads_legal_files_formset']

        if ads_users_formset.is_valid() and ads_legal_files_formset.is_valid():
            resp = super().form_valid(form)
            ads_users_formset.instance = self.object
            ads_users_formset.save()
            ads_legal_files_formset.instance = self.object
            ads_legal_files_formset.save()
            return resp
        return super().form_invalid(form)


class ADSDeleteView(DeleteView):
    template_name = 'pages/ads_confirm_delete.html'
    model = ADS
    pk_url_kwarg = 'ads_id'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['ads_manager'] = ADSManager.objects.get(id=self.kwargs['manager_id'])
        return ctx

    def get_success_url(self):
        return reverse('app.ads-manager.detail', kwargs={
            'manager_id': self.kwargs['manager_id'],
        })


class ADSCreateView(ADSView, CreateView):

    def dispatch(self, request, manager_id):
        """If the ADSManager has the flag no_ads_declared to True, it is
        imposisble to create ADS for it."""
        get_object_or_404(ADSManager, id=manager_id, no_ads_declared=False)
        return super().dispatch(request, manager_id)

    def get_object(self, queryset=None):
        return None

    def get_success_url(self):
        return reverse('app.ads.detail', kwargs={
            'manager_id': self.kwargs['manager_id'],
            'ads_id': self.object.id,
        })

    def form_valid(self, form):
        ads_manager = ADSManager.objects.get(id=self.kwargs['manager_id'])
        form.instance.ads_manager = ads_manager

        # CreateView doesn't call form.validate_unique(). The try/catch below
        # attemps to save the object. If IntegrityError is returned from
        # database, we return a custom error message for "number".
        try:
            with transaction.atomic():
                return super().form_valid(form)
        except IntegrityError:
            form.add_error('number', ADS.UNIQUE_ERROR_MSG)
            return super().form_invalid(form)


def prefecture_export_ads(request, ads_manager_administrator):
    prefecture = ads_manager_administrator.prefecture
    response = HttpResponse(
        content_type='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename="ADS_prefecture_%s.csv"' % prefecture.numero
        },
    )

    def display_bool(value):
        if value is None:
            return ''
        return 'oui' if value else 'non'

    fields = [
        ('Administration', lambda ads: ads.ads_manager.content_object.display_text()),
        ('Numéro', lambda ads: ads.number),
        ('Date de création', lambda ads: ads.ads_creation_date),
        ("Type", lambda ads: ads.ads_type and dict(ADS.ads_type.field.choices)[ads.ads_type]),
        ("Date d'attribution au titulaire actuel", lambda ads: ads.attribution_date),
        ("Type d'attribution", lambda ads: ads.attribution_type and dict(ADS.attribution_type.field.choices)[ads.attribution_type]),
        ("Raison de l'attribution", lambda ads: ads.attribution_reason),
        ("Conventionné CPAM ?", lambda ads: display_bool(ads.accepted_cpam)),
        ("Plaque d'immatriculation", lambda ads: ads.immatriculation_plate),
        ("Véhicule compatible PMR ?", lambda ads: display_bool(ads.vehicle_compatible_pmr)),
        ("Véhicule électrique ou hybride ?", lambda ads: display_bool(ads.eco_vehicle)),
        ("Nom du titulaire", lambda ads: ads.owner_name),
        ("SIRET titulaire", lambda ads: ads.owner_siret),
        ("ADS exploitée par le titulaire ?", lambda ads: display_bool(ads.used_by_owner)),
        ("Statuts des exploitants (un par ligne)", lambda ads: '\n'.join([
            dict(ADSUser.status.field.choices)[status] if status else ''
            for status in ads.ads_users_status
        ])),
        ("Noms des exploitants (un par ligne)", lambda ads: '\n'.join([
            name or '' for name in ads.ads_users_names
        ])),
        ("SIRET des exploitants (un par ligne)", lambda ads: '\n'.join([
            siret or '' for siret in ads.ads_users_sirets
        ])),
    ]

    writer = csv.DictWriter(response, fieldnames=[field[0] for field in fields])

    writer.writeheader()

    for ads in ADS.objects.select_related(
        'ads_manager__administrator__prefecture',
    ).prefetch_related(
        'ads_manager__content_object',
    ).filter(
        ads_manager__administrator=ads_manager_administrator
    ).annotate(
        ads_users_status=ArrayAgg('adsuser__status'),
        ads_users_names=ArrayAgg('adsuser__name'),
        ads_users_sirets=ArrayAgg('adsuser__siret'),
    ):
        writer.writerow({
            field[0]: field[1](ads)
            for field in fields
        })

    return response


class DashboardsView(TemplateView):

    template_name = 'pages/dashboards_list.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['stats'] = self.get_stats()
        return ctx

    def get_stats(self):
        """Get a list of ADSManagerAdministrator instances the following statistics:
            - number of ADS (now, and 3/6/12 months ago)
            - number of ADSManager accounts (now, and 3/6/12 months ago)

        >>> [
        ...      obj: <ADSManagerAdministrator object>
        ...      'ads': {
        ...          'now': <int, number of ADS currently registered>
        ...          '3_months': <number of ADS updated less than 3 months ago>
        ...          '6_months':
        ...          '12_months':
        ...      },
        ...      'users': {
        ...          'now': <int, number of users with permissions to create ADS>
        ...          '3_months': <number of users 3 months ago>
        ...          '6_months':
        ...          '12_months':
        ...       }
        ...  ]
        """
        now = timezone.now()

        stats = collections.defaultdict(lambda: {
            'obj': None,
            'ads': {},
            'users': {}
        })

        ads_query_now = ADSManagerAdministrator.objects \
            .select_related('prefecture') \
            .annotate(ads_count=Count('adsmanager__ads')) \
            .filter(ads_count__gt=0)

        # All ADSManagerAdministrator, with the count of ADS with at least one of the contact fields filled.
        ads_with_info_query_now = ADSManagerAdministrator.objects \
            .select_related('prefecture') \
            .annotate(ads_count=Count(
                'adsmanager__ads',
                filter=~Q(adsmanager__ads__owner_email='') | ~Q(adsmanager__ads__owner_mobile='') | ~Q(adsmanager__ads__owner_phone='')
            )) \
            .filter(ads_count__gt=0)

        ads_query_3_months = ADSManagerAdministrator.objects \
            .select_related('prefecture') \
            .filter(adsmanager__ads__creation_date__lte=now - timedelta(weeks=4 * 3)) \
            .annotate(ads_count=Count('adsmanager__ads'))

        ads_query_6_months = ADSManagerAdministrator.objects \
            .select_related('prefecture') \
            .filter(adsmanager__ads__creation_date__lte=now - timedelta(weeks=4 * 6)) \
            .annotate(ads_count=Count('adsmanager__ads'))

        ads_query_12_months = ADSManagerAdministrator.objects \
            .select_related('prefecture') \
            .filter(adsmanager__ads__creation_date__lte=now - timedelta(weeks=4 * 12)) \
            .annotate(ads_count=Count('adsmanager__ads'))

        for (label, query) in (
            ('now', ads_query_now),
            ('with_info_now', ads_with_info_query_now),
            ('3_months', ads_query_3_months),
            ('6_months', ads_query_6_months),
            ('12_months', ads_query_12_months),
        ):
            for row in query:
                stats[row.prefecture.id]['obj'] = row
                stats[row.prefecture.id]['ads'][label] = row.ads_count

        users_query_now = ADSManagerAdministrator.objects \
            .select_related('prefecture') \
            .filter(adsmanager__adsmanagerrequest__accepted=True) \
            .annotate(users_count=Count('id'))

        users_query_3_months = ADSManagerAdministrator.objects \
            .select_related('prefecture') \
            .filter(
                adsmanager__adsmanagerrequest__accepted=True,
                adsmanager__adsmanagerrequest__created_at__lte=now - timedelta(weeks=4 * 3)
            ).annotate(users_count=Count('id'))

        users_query_6_months = ADSManagerAdministrator.objects \
            .select_related('prefecture') \
            .filter(
                adsmanager__adsmanagerrequest__accepted=True,
                adsmanager__adsmanagerrequest__created_at__lte=now - timedelta(weeks=4 * 6)
            ).annotate(users_count=Count('id'))

        users_query_12_months = ADSManagerAdministrator.objects \
            .select_related('prefecture') \
            .filter(
                adsmanager__adsmanagerrequest__accepted=True,
                adsmanager__adsmanagerrequest__created_at__lte=now - timedelta(weeks=4 * 12)
            ).annotate(users_count=Count('id'))

        for (label, query) in (
            ('now', users_query_now),
            ('3_months', users_query_3_months),
            ('6_months', users_query_6_months),
            ('12_months', users_query_12_months),
        ):
            for row in query.all():
                stats[row.prefecture.id]['obj'] = row
                stats[row.prefecture.id]['users'][label] = row.users_count

        # Transform dict to an ordered list
        return sorted(list(stats.values()), key=lambda stat: stat['obj'].id)


class DashboardsDetailView(DetailView):
    template_name = 'pages/dashboards_detail.html'
    model = ADSManagerAdministrator
    pk_url_kwarg = 'ads_manager_administrator_id'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['stats'] = self.get_stats()
        return ctx

    def get_stats(self):
        stats = {}

        stats = collections.defaultdict(lambda: {
            'obj': None,
            'ads': {},
            'users': {}
        })

        now = timezone.now()

        ads_query_now = ADSManager.objects \
            .prefetch_related('content_type', 'content_object') \
            .filter(
                administrator=self.object
            ).annotate(ads_count=Count('ads')) \
            .filter(ads_count__gt=0)

        # All ADSManager, with the count of ADS with at least one of the contact fields filled.
        ads_with_info_query_now = ADSManager.objects \
            .prefetch_related('content_type', 'content_object') \
            .filter(
                administrator=self.object
            ).annotate(ads_count=Count('ads', filter=~Q(ads__owner_email='') | ~Q(ads__owner_mobile='') | ~Q(ads__owner_phone=''))) \
            .filter(ads_count__gt=0)

        ads_query_3_months = ADSManager.objects \
            .prefetch_related('content_type', 'content_object') \
            .filter(
                administrator=self.object,
                ads__creation_date__lte=now - timedelta(weeks=4 * 3)
            ).annotate(ads_count=Count('ads'))

        ads_query_6_months = ADSManager.objects \
            .prefetch_related('content_type', 'content_object') \
            .filter(
                administrator=self.object,
                ads__creation_date__lte=now - timedelta(weeks=4 * 6)
            ).annotate(ads_count=Count('ads'))

        ads_query_12_months = ADSManager.objects \
            .prefetch_related('content_type', 'content_object') \
            .filter(
                administrator=self.object,
                ads__creation_date__lte=now - timedelta(weeks=4 * 12)
            ).annotate(ads_count=Count('ads'))

        for (label, query) in (
            ('now', ads_query_now),
            ('with_info_now', ads_with_info_query_now),
            ('3_months', ads_query_3_months),
            ('6_months', ads_query_6_months),
            ('12_months', ads_query_12_months),
        ):
            for row in query:
                stats[row.id]['obj'] = row
                stats[row.id]['ads'][label] = row.ads_count

        users_query_now = ADSManager.objects \
            .prefetch_related('content_type', 'content_object') \
            .filter(
                administrator=self.object,
                adsmanagerrequest__accepted=True
            ).annotate(users_count=Count('id'))

        users_query_3_months = ADSManager.objects \
            .prefetch_related('content_type', 'content_object') \
            .filter(
                administrator=self.object,
                adsmanagerrequest__accepted=True,
                adsmanagerrequest__created_at__lte=now - timedelta(weeks=4 * 3),
            ).annotate(users_count=Count('id'))

        users_query_6_months = ADSManager.objects \
            .prefetch_related('content_type', 'content_object') \
            .filter(
                administrator=self.object,
                adsmanagerrequest__accepted=True,
                adsmanagerrequest__created_at__lte=now - timedelta(weeks=4 * 6),
            ).annotate(users_count=Count('id'))

        users_query_12_months = ADSManager.objects \
            .prefetch_related('content_type', 'content_object') \
            .filter(
                administrator=self.object,
                adsmanagerrequest__accepted=True,
                adsmanagerrequest__created_at__lte=now - timedelta(weeks=4 * 12),
            ).annotate(users_count=Count('id'))

        for (label, query) in (
            ('now', users_query_now),
            ('3_months', users_query_3_months),
            ('6_months', users_query_6_months),
            ('12_months', users_query_12_months),
        ):
            for row in query.all():
                stats[row.id]['obj'] = row
                stats[row.id]['users'][label] = row.users_count

        return sorted(list(stats.values()), key=lambda stat: stat['obj'].id)


class FAQView(TemplateView):
    template_name = 'pages/faq.html'
    faq_sections = [
        {
            "title": "Gestion du compte",
            "subitems": [
                {
                    "title": "Comment créer un compte ?",
                    "template": "pages/faq/account_create.html"
                },
                {
                    "title": "Je ne reçois pas l'e-mail de validation",
                    "template": "pages/faq/account_email_not_received.html",
                },
                {
                    "title": "Comment configurer l'accès gestionnaire ?",
                    "template": "pages/faq/account_send_request.html",
                },
                {
                    "title": "J'ai oublié mon mot de passe",
                    "template": "pages/faq/account_forgot_password.html",
                },
                {
                    "title": "Je veux changer l'adresse e-mail de mon compte",
                    "template": "pages/faq/account_change_email.html",
                },
            ],
        },
        {
            "title": "Gestion des ADS",
            "subitems": [
                {
                    "title": "Créer, modifier et supprimer une ADS",
                    "template": "pages/faq/ads_manage.html",
                },
                {
                    "title": "Pour les préfectures",
                    "subitems": [
                        {
                            "title": "Comment valider les demandes d'accès des agents territoriaux ?",
                            "template": "pages/faq/ads_prefecture_manage.html",
                        },
                        {
                            "title": "Comment révoquer un accès ?",
                            "template": "pages/faq/ads_prefecture_revoke.html",
                        },
                    ],
                },
            ],
        },
        {
            "title": "Problème technique, remarque, question",
            "template": "pages/faq/contact.html",
        }
    ]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['faq_sections'] = self.faq_sections
        return ctx
