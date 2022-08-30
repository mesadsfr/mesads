import collections
import csv
from datetime import timedelta

from django.conf import settings
from django.contrib.messages.views import SuccessMessageMixin
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
from django.views.generic import TemplateView
from django.views.generic import UpdateView
from django.views.generic.edit import CreateView, DeleteView, FormView
from django.views.generic.list import ListView

from reversion.views import RevisionMixin

from .forms import (
    ADSSearchForm,
    ADSManagerForm,
    ADSUserFormSet,
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
    redirect to ads-manager-admin or ads-manager-request depending on
    permissions.
    """
    template_name = 'pages/homepage.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_staff:
            return redirect(reverse('dashboards'))
        if len(self.request.user.adsmanageradministrator_set.all()):
            return redirect(reverse('ads-manager-admin'))
        return redirect(reverse('ads-manager-request'))


class ADSManagerAdminView(RevisionMixin, TemplateView):
    template_name = 'pages/ads_manager_admin.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx['ads_manager_requests'] = {}

        # Get all ADSManagerAdministrator objects related to the current user
        ads_manager_admins = ADSManagerAdministrator.objects.filter(users__in=[self.request.user])

        # For each admin, get the list of requests
        for ads_manager_admin in ads_manager_admins:
            ads_manager_requests = ADSManagerRequest.objects.filter(
                ads_manager__in=[obj.id for obj in ads_manager_admin.ads_managers.all()]
            ).order_by('-id')
            ctx['ads_manager_requests'][ads_manager_admin] = ads_manager_requests
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
            ads_managers__in=[ads_manager_request.ads_manager]
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
        return redirect(reverse('ads-manager-admin'))


class ADSManagerRequestView(SuccessMessageMixin, FormView):
    template_name = 'pages/ads_manager_request.html'
    form_class = ADSManagerForm
    success_url = reverse_lazy('ads-manager-request')

    def get_context_data(self, **kwargs):
        """Expose the list of ADSManagerAdministrators for which current user
        is configured.

        It is also accessible through user.adsmanageradministrator_set.all, but
        we need to prefetch ads_managers__content_object to reduce the number
        of SQL queries generated.
        """
        ctx = super().get_context_data(**kwargs)
        ctx['ads_managers_administrators'] = ADSManagerAdministrator.objects.filter(
            users__in=[self.request.user]
        ).prefetch_related('ads_managers__content_object')
        return ctx

    def form_valid(self, form):
        ADSManagerRequest.objects.get_or_create(
            user=self.request.user,
            ads_manager=form.cleaned_data['ads_manager'],
        )

        # Send notifications to administrators.
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

        for administrator_user in form.cleaned_data['ads_manager'].get_administrators_users():
            send_mail(
                email_subject,
                email_content,
                settings.MESADS_CONTACT_EMAIL,
                [administrator_user],
                fail_silently=True,
            )

        return super().form_valid(form)

    def get_success_message(self, cleaned_data):
        prefectures = [
            ads_manager_administrator.prefecture
            for ads_manager_administrator in
            cleaned_data['ads_manager'].adsmanageradministrator_set.all()
        ]

        # Request for EPCI or prefectures
        if not prefectures:
            return '''
                Votre demande vient d’être envoyée à notre équipe. Vous recevrez une confirmation de validation de votre
                accès par mail.<br /><br />

                En cas de difficulté ou si vous n’obtenez pas de validation de votre demande vous pouvez contacter
                <a href="mailto:%(email)s">%(email)s</a>.<br /><br />

                Vous pouvez également demander un accès pour la gestion des ADS d’une autre collectivité.
            ''' % {
                'email': settings.MESADS_CONTACT_EMAIL
            }

        return '''
            Votre demande vient d’être envoyée à %(prefectures)s. Vous recevrez une confirmation de validation de votre
            accès par mail.<br /><br />

            En cas de difficulté ou si vous n’obtenez pas de validation de votre demande vous pouvez
            contacter <a href="mailto:%(email)s">%(email)s</a>.<br /><br />

            Vous pouvez également demander un accès pour la gestion des ADS d’une autre collectivité.
        ''' % {
            'prefectures': ', '.join([prefecture.display_fulltext() for prefecture in prefectures]),
            'email': settings.MESADS_CONTACT_EMAIL
        }


class ADSManagerView(ListView):
    template_name = 'pages/ads_manager.html'
    model = ADS
    paginate_by = 50

    def _get_form(self):
        return ADSSearchForm(self.request.GET)

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(ads_manager__id=self.kwargs['manager_id'])

        form = self._get_form()
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
            select={'ads_number_as_int': "CAST(substring(number FROM '^[0-9]+') AS INTEGER)"}
        )

        # First, order by number if it is an integer, then by string.
        return qs_ordered.annotate(c=Count('id')).order_by('ads_number_as_int', 'number')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search_form'] = self._get_form()
        ctx['ads_manager'] = ADSManager.objects.get(id=self.kwargs['manager_id'])
        return ctx


class ADSView(RevisionMixin, UpdateView):
    template_name = 'pages/ads.html'
    model = ADS
    fields = (
        'number',
        'ads_creation_date',
        'ads_type',
        'attribution_date',
        'attribution_type',
        'transaction_identifier',
        'attribution_reason',
        'accepted_cpam',
        'immatriculation_plate',
        'vehicle_compatible_pmr',
        'eco_vehicle',
        'owner_name',
        'owner_siret',
        'owner_phone',
        'owner_mobile',
        'owner_email',
        'used_by_owner',
        'legal_file',
    )

    def get_success_url(self):
        return reverse('ads', kwargs={
            'manager_id': self.kwargs['manager_id'],
            'ads_id': self.kwargs['ads_id'],
        })

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['ads_manager'] = ADSManager.objects.get(id=self.kwargs['manager_id'])

        if self.request.POST:
            ctx['ads_users_formset'] = ADSUserFormSet(self.request.POST, instance=self.object)
        else:
            ctx['ads_users_formset'] = ADSUserFormSet(instance=self.object)
        return ctx

    def get_object(self, queryset=None):
        return get_object_or_404(ADS, id=self.kwargs['ads_id'])

    def form_valid(self, form):
        ctx = self.get_context_data()
        ads_users_formset = ctx['ads_users_formset']
        if ads_users_formset.is_valid():
            resp = super().form_valid(form)
            ads_users_formset.instance = self.object
            ads_users_formset.save()
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
        return reverse('ads-manager', kwargs={
            'manager_id': self.kwargs['manager_id'],
        })


class ADSCreateView(ADSView, CreateView):
    def get_object(self, queryset=None):
        return None

    def get_success_url(self):
        return reverse('ads', kwargs={
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
            dict(ADSUser.status.field.choices)[ads_user.status] if ads_user.status else ''
            for ads_user in ads.adsuser_set.all()
        ])),
        ("Noms des exploitants (un par ligne)", lambda ads: '\n'.join([
            ads_user.name
            for ads_user in ads.adsuser_set.all()
        ])),
        ("SIRET des exploitants (un par ligne)", lambda ads: '\n'.join([
            ads_user.siret
            for ads_user in ads.adsuser_set.all()
        ])),
    ]

    writer = csv.DictWriter(response, fieldnames=[field[0] for field in fields])

    writer.writeheader()

    for ads in ADS.objects.prefetch_related(
        'ads_manager__content_object',
        'adsuser_set',
    ).filter(ads_manager__in=ads_manager_administrator.ads_managers.all()):
        writer.writerow({
            field[0]: field[1](ads)
            for field in fields
        })

    return response


class DashboardsView(TemplateView):

    template_name = 'pages/dashboards.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['stats'] = self._get_stats()
        return ctx

    def _get_stats(self):
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
        ...      'ads_managers': {
        ...          'now': <int, number of ADS managers>
        ...          '3_months': <number of managers 3 months ago>
        ...          '6_months':
        ...          '12_months':
        ...       }
        ...  ]
        """
        now = timezone.now()

        stats = collections.defaultdict(lambda: {
            'obj': None,
            'ads': {},
            'ads_managers': {}
        })

        ads_query_now = ADSManagerAdministrator.objects \
            .select_related('prefecture') \
            .annotate(ads_count=Count('ads_managers__ads')) \
            .filter(ads_count__gt=0)

        ads_query_3_months = ADSManagerAdministrator.objects \
            .select_related('prefecture') \
            .filter(ads_managers__ads__creation_date__lte=now - timedelta(weeks=4 * 3)) \
            .annotate(ads_count=Count('ads_managers__ads'))

        ads_query_6_months = ADSManagerAdministrator.objects \
            .select_related('prefecture') \
            .filter(ads_managers__ads__creation_date__lte=now - timedelta(weeks=4 * 6)) \
            .annotate(ads_count=Count('ads_managers__ads'))

        ads_query_12_months = ADSManagerAdministrator.objects \
            .select_related('prefecture') \
            .filter(ads_managers__ads__creation_date__lte=now - timedelta(weeks=4 * 12)) \
            .annotate(ads_count=Count('ads_managers__ads'))

        for (label, query) in (
            ('now', ads_query_now),
            ('3_months', ads_query_3_months),
            ('6_months', ads_query_6_months),
            ('12_months', ads_query_12_months),
        ):
            for row in query:
                stats[row.prefecture.id]['obj'] = row
                stats[row.prefecture.id]['ads'][label] = row.ads_count

        ads_managers_query_now = ADSManagerAdministrator.objects \
            .select_related('prefecture') \
            .filter(ads_managers__adsmanagerrequest__accepted=True) \
            .annotate(ads_managers_count=Count('id'))

        ads_managers_query_3_months = ADSManagerAdministrator.objects \
            .select_related('prefecture') \
            .filter(
                ads_managers__adsmanagerrequest__accepted=True,
                ads_managers__adsmanagerrequest__created_at__lte=now - timedelta(weeks=4 * 3)
            ).annotate(ads_managers_count=Count('id'))

        ads_managers_query_6_months = ADSManagerAdministrator.objects \
            .select_related('prefecture') \
            .filter(
                ads_managers__adsmanagerrequest__accepted=True,
                ads_managers__adsmanagerrequest__created_at__lte=now - timedelta(weeks=4 * 6)
            ).annotate(ads_managers_count=Count('id'))

        ads_managers_query_12_months = ADSManagerAdministrator.objects \
            .select_related('prefecture') \
            .filter(
                ads_managers__adsmanagerrequest__accepted=True,
                ads_managers__adsmanagerrequest__created_at__lte=now - timedelta(weeks=4 * 12)
            ).annotate(ads_managers_count=Count('id'))

        for (label, query) in (
            ('now', ads_managers_query_now),
            ('3_months', ads_managers_query_3_months),
            ('6_months', ads_managers_query_6_months),
            ('12_months', ads_managers_query_12_months),
        ):
            for row in query.all():
                stats[row.prefecture.id]['obj'] = row
                stats[row.prefecture.id]['ads_managers'][label] = row.ads_managers_count

        # Transform dict to an ordered list
        return sorted(list(stats.values()), key=lambda stat: stat['obj'].id)
