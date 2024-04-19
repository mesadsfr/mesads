from datetime import date, datetime, timedelta
import collections
import json

from docxtpl import DocxTemplate

from django.conf import settings
from django.contrib import messages
from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.staticfiles import finders
from django.core.exceptions import SuspiciousOperation
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.db.models import Count, Q, Sum, Value
from django.db.models.functions import Coalesce, Replace, TruncMonth
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.template.defaultfilters import date as date_template_filter
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import RedirectView, TemplateView, UpdateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, DeleteView, FormView, ProcessFormView
from django.views.generic.list import ListView

import xlsxwriter

from formtools.wizard.views import CookieWizardView

from reversion.views import RevisionMixin

from mesads.fradm.models import EPCI

from .forms import (
    ADSDecreeForm1,
    ADSDecreeForm2,
    ADSDecreeForm3,
    ADSDecreeForm4,
    ADSForm,
    ADSLegalFileFormSet,
    ADSManagerDecreeFormSet,
    ADSManagerEditForm,
    ADSManagerForm,
    ADSSearchForm,
    ADSUserFormSet,
)
from .models import (
    ADS,
    ADSLegalFile,
    ADSManager,
    ADSManagerAdministrator,
    ADSManagerRequest,
    ADSUser,
)
from .reversion_diff import ModelHistory


class HTTP500View(TemplateView):
    """The default HTTP/500 handler can't access to context processors and does
    not have access to the variable MESADS_CONTACT_EMAIL.
    """

    template_name = "500.html"

    def dispatch(self, request, *args, **kwargs):
        """The base class TemplateView only accepts GET requests. By overriding
        dispatch, we return the error page for any other method."""
        return super().get(request, *args, **kwargs)


class HomepageView(TemplateView):
    template_name = "pages/homepage.html"


class ADSRegisterView(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        if self.request.user.is_staff:
            return reverse("app.dashboards.list")
        if len(self.request.user.adsmanageradministrator_set.all()):
            return reverse("app.ads-manager-admin.index")
        return reverse("app.ads-manager.index")


class ADSManagerAdminView(RevisionMixin, TemplateView):
    template_name = "pages/ads_register/ads_manager_admin.html"

    def get_context_data(self, **kwargs):
        """Populate context with the list of ADSManagerRequest current user can accept."""
        ctx = super().get_context_data(**kwargs)
        query = (
            ADSManagerRequest.objects.select_related(
                "ads_manager__administrator",
                "ads_manager__administrator__prefecture",
                "ads_manager__content_type",
                "user",
            )
            .prefetch_related("ads_manager__content_object")
            .filter(ads_manager__administrator__users__in=[self.request.user])
        )
        if self.request.GET.get("sort") == "name":
            ctx["sort"] = "name"
            ctx["ads_manager_requests"] = query.order_by(
                "ads_manager__administrator",
                "ads_manager__commune__libelle",
                "ads_manager__epci__name",
                "ads_manager__prefecture__libelle",
            )
        else:
            ctx["ads_manager_requests"] = query.order_by(
                "ads_manager__administrator",
                "-created_at",
            )
        return ctx

    def post(self, request):
        request_id = request.POST.get("request_id")
        action = request.POST.get("action")

        if action not in ("accept", "deny"):
            raise SuspiciousOperation("Invalid action")

        ads_manager_request = get_object_or_404(ADSManagerRequest, id=request_id)

        # Make sure current user can accept this request
        get_object_or_404(
            ADSManagerAdministrator,
            users__in=[request.user],
            adsmanager=ads_manager_request.ads_manager,
        )

        if action == "accept":
            ads_manager_request.accepted = True
        else:
            ads_manager_request.accepted = False
        ads_manager_request.save()

        # Send notification to user
        email_subject = render_to_string(
            "pages/email_ads_manager_request_result_subject.txt",
            {
                "ads_manager_request": ads_manager_request,
            },
            request=request,
        ).strip()
        email_content = render_to_string(
            "pages/email_ads_manager_request_result_content.txt",
            {
                "request": request,
                "ads_manager_request": ads_manager_request,
            },
            request=request,
        )
        email_content_html = render_to_string(
            "pages/email_ads_manager_request_result_content.mjml",
            {
                "request": request,
                "ads_manager_request": ads_manager_request,
            },
            request=request,
        )
        send_mail(
            email_subject,
            email_content,
            settings.MESADS_CONTACT_EMAIL,
            [ads_manager_request.user.email],
            fail_silently=True,
            html_message=email_content_html,
        )
        return redirect(reverse("app.ads-manager-admin.index"))


class ADSManagerRequestView(FormView):
    template_name = "pages/ads_register/ads_manager_request.html"
    form_class = ADSManagerForm
    success_url = reverse_lazy("app.ads-manager.index")

    def get_context_data(self, **kwargs):
        """Expose the list of ADSManagerAdministrators for which current user
        is configured.

        It is also accessible through user.adsmanageradministrator_set.all, but
        we need to prefetch ads_managers__content_object to reduce the number
        of SQL queries generated.
        """
        ctx = super().get_context_data(**kwargs)
        ctx["user_ads_manager_requests"] = (
            ADSManagerRequest.objects.filter(user=self.request.user)
            .annotate(ads_count=Count("ads_manager__ads"))
            .all()
        )

        ctx["ads_managers_administrators"] = (
            ADSManagerAdministrator.objects.select_related("prefecture")
            .filter(users=self.request.user)
            .all()
        )
        return ctx

    def form_valid(self, form):
        _, created = ADSManagerRequest.objects.get_or_create(
            user=self.request.user,
            ads_manager=form.cleaned_data["ads_manager"],
        )

        # Request already exists
        if not created:
            messages.warning(
                self.request,
                self.get_message_for_existing_request(form.cleaned_data["ads_manager"]),
            )
        # Send notifications to administrators.
        else:
            messages.success(
                self.request,
                self.get_message_for_new_request(form.cleaned_data["ads_manager"]),
            )
            email_subject = render_to_string(
                "pages/email_ads_manager_request_administrator_subject.txt",
                {
                    "user": self.request.user,
                },
                request=self.request,
            ).strip()
            email_content = render_to_string(
                "pages/email_ads_manager_request_administrator_content.txt",
                {
                    "request": self.request,
                    "ads_manager": form.cleaned_data["ads_manager"],
                    "user": self.request.user,
                },
                request=self.request,
            )
            email_content_html = render_to_string(
                "pages/email_ads_manager_request_administrator_content.mjml",
                {
                    "request": self.request,
                    "ads_manager": form.cleaned_data["ads_manager"],
                    "user": self.request.user,
                },
                request=self.request,
            )

            if form.cleaned_data["ads_manager"].administrator:
                for administrator_user in form.cleaned_data[
                    "ads_manager"
                ].administrator.users.all():
                    send_mail(
                        email_subject,
                        email_content,
                        settings.MESADS_CONTACT_EMAIL,
                        [administrator_user],
                        fail_silently=True,
                        html_message=email_content_html,
                    )

        return super().form_valid(form)

    def get_message_for_existing_request(self, ads_manager):
        if not ads_manager.administrator:
            return """
                Vous avez déjà effectué une demande pour gérer les ADS de %(administration)s, et notre équipe va y répondre dans les plus brefs délais.<br /><br />

                Si vous n'avez eu aucun retour depuis plusieurs jours, n'hésitez pas à contacter notre équipe par email à <a href="mailto:%(email)s">%(email)s</a> ou via notre module de tchat.
            """ % {
                "email": settings.MESADS_CONTACT_EMAIL,
                "administration": ads_manager.content_object.display_fulltext(),
            }
        return """
            Vous avez déjà effectué une demande pour gérer les ADS de %(administration)s. Cette demande a été envoyée à %(prefecture)s qui devrait y répondre rapidement.<br /><br />

            Si vous n'avez eu aucun retour depuis plusieurs jours, n'hésitez pas à nous signaler le problème par email à <a href="mailto:%(email)s">%(email)s</a> ou via notre module de tchat.
            <br /><br />
            Nous pourrons alors valider votre demande manuellement.
        """ % {
            "administration": ads_manager.content_object.display_fulltext(),
            "prefecture": ads_manager.administrator.prefecture.display_fulltext(),
            "email": settings.MESADS_CONTACT_EMAIL,
        }

    def get_message_for_new_request(self, ads_manager):
        # Request for EPCI or prefectures
        if not ads_manager.administrator:
            return """
                Votre demande vient d’être envoyée à notre équipe. Vous recevrez une confirmation de validation de votre
                accès par mail.<br /><br />

                En cas de difficulté ou si vous n’obtenez pas de validation de votre demande vous pouvez contacter par email à
                <a href="mailto:%(email)s">%(email)s</a> ou via notre module de tchat.<br /><br />

                Vous pouvez également demander un accès pour la gestion des ADS d’une autre collectivité.
            """ % {
                "email": settings.MESADS_CONTACT_EMAIL
            }

        return """
            Votre demande vient d’être envoyée à %(prefecture)s. Vous recevrez une confirmation de validation de votre
            accès par mail.<br /><br />

            En cas de difficulté ou si vous n’obtenez pas de validation de votre demande vous pouvez
            contacter par email à <a href="mailto:%(email)s">%(email)s</a> ou via notre module de tchat.<br /><br />

            Vous pouvez également demander un accès pour la gestion des ADS d’une autre collectivité.
        """ % {
            "prefecture": ads_manager.administrator.prefecture.display_fulltext(),
            "email": settings.MESADS_CONTACT_EMAIL,
        }


class ADSManagerView(ListView, ProcessFormView):
    template_name = "pages/ads_register/ads_manager.html"
    model = ADS
    paginate_by = 50

    def get(self, request, *args, **kwargs):
        self.search_form = ADSSearchForm(request.GET)
        return ListView.get(self, request, *args, **kwargs)

    def get_ads_manager(self):
        return ADSManager.objects.get(id=self.kwargs["manager_id"])

    def get_form(self):
        if self.request.method == "POST":
            return ADSManagerEditForm(
                instance=self.get_ads_manager(), data=self.request.POST
            )
        return ADSManagerEditForm(instance=self.get_ads_manager())

    def form_valid(self, form):
        form.save()
        return redirect("app.ads-manager.detail", manager_id=self.kwargs["manager_id"])

    def form_invalid(self, form):
        return self.get(self.request, *self.args, **self.kwargs)

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(ads_manager__id=self.kwargs["manager_id"])

        if self.search_form.is_valid():
            if self.search_form.cleaned_data["accepted_cpam"] is not None:
                qs = qs.filter(
                    accepted_cpam=self.search_form.cleaned_data["accepted_cpam"]
                )

            q = self.search_form.cleaned_data["q"]
            if q:
                qs = qs.annotate(
                    clean_immatriculation_plate=Replace(
                        "immatriculation_plate", Value("-"), Value("")
                    )
                )

                qs = qs.filter(
                    Q(owner_siret__icontains=q)
                    | Q(adsuser__name__icontains=q)
                    | Q(adsuser__siret__icontains=q)
                    | Q(owner_name__icontains=q)
                    | Q(clean_immatriculation_plate__icontains=q)
                    | Q(epci_commune__libelle__icontains=q)
                    | Q(number__icontains=q)
                )

        # Add ordering on the number. CAST is necessary in the case the ADS number is not an integer.
        qs_ordered = qs.extra(
            select={
                "ads_number_as_int": "CAST(substring(number FROM '^[0-9]+') AS NUMERIC)"
            }
        )

        # First, order by number if it is an integer, then by string.
        return qs_ordered.annotate(c=Count("id")).order_by(
            "ads_number_as_int", "number"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_form"] = self.search_form

        # search_defined is a boolean, set to True of any of the search form
        # parameter is defined.
        ctx["search_defined"] = any(
            (v is not None and v != "" for v in self.search_form.cleaned_data.values())
        )

        ctx["edit_form"] = self.get_form()
        ctx["ads_manager"] = ctx["edit_form"].instance
        return ctx


class ADSView(RevisionMixin, UpdateView):
    template_name = "pages/ads_register/ads.html"
    form_class = ADSForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        # If manager_id is the primary key of an EPCI, initialize ADSForm with
        # the parameter "epci" which is required to setup autocompletion for the
        # field ADS.epci_commune. This field is not displayed if the manager is
        # a Prefecture or a Commune.
        ads_manager = get_object_or_404(ADSManager, id=self.kwargs["manager_id"])
        if ads_manager.content_type.model_class() is EPCI:
            kwargs["epci"] = ads_manager.content_object

        return kwargs

    def get_success_url(self):
        return reverse(
            "app.ads.detail",
            kwargs={
                "manager_id": self.kwargs["manager_id"],
                "ads_id": self.kwargs["ads_id"],
            },
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["ads_manager"] = ADSManager.objects.get(id=self.kwargs["manager_id"])
        ctx["ads_users_formset"] = self.ads_users_formset
        ctx["ads_legal_files_formset"] = self.ads_legal_files_formset
        return ctx

    def get_object(self, queryset=None):
        ads = get_object_or_404(ADS, id=self.kwargs["ads_id"])

        if self.request.POST and self.request.POST.get(
            ADSUserFormSet().management_form["TOTAL_FORMS"].html_name
        ):
            self.ads_users_formset = ADSUserFormSet(self.request.POST, instance=ads)
        else:
            self.ads_users_formset = ADSUserFormSet(instance=ads)
            # Always display at least a form
            if not ads.adsuser_set.count():
                self.ads_users_formset.extra = 1

        if self.request.POST and self.request.POST.get(
            ADSLegalFileFormSet().management_form["TOTAL_FORMS"].html_name
        ):
            self.ads_legal_files_formset = ADSLegalFileFormSet(
                self.request.POST, self.request.FILES, instance=ads
            )
        else:
            self.ads_legal_files_formset = ADSLegalFileFormSet(instance=ads)

        return ads

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Le formulaire contient des erreurs. Veuillez les corriger avant de soumettre à nouveau.",
        )
        return super().form_invalid(form)

    @transaction.atomic
    def form_valid(self, form):
        html_name_ads_users_formset = self.ads_users_formset.management_form[
            "TOTAL_FORMS"
        ].html_name
        if (
            self.request.POST.get(html_name_ads_users_formset) is not None
            and not self.ads_users_formset.is_valid()
        ):
            return self.form_invalid(form)

        html_name_ads_legal_files_formset = (
            self.ads_legal_files_formset.management_form["TOTAL_FORMS"].html_name
        )
        if (
            self.request.POST.get(html_name_ads_legal_files_formset) is not None
            and not self.ads_legal_files_formset.is_valid()
        ):
            return self.form_invalid(form)

        self.object = form.save(check=False)
        self.ads_users_formset.instance = self.object
        self.ads_legal_files_formset.instance = self.object

        if not self.request.POST.get(html_name_ads_users_formset):
            ADSUser.objects.filter(ads=self.object).delete()
        else:
            try:
                with transaction.atomic():
                    self.ads_users_formset.save()
            except IntegrityError:
                errmsg = [
                    c
                    for c in ADSUser._meta.constraints
                    if c.name == "only_one_titulaire_exploitant"
                ][0].violation_error_message
                self.ads_users_formset.non_form_errors().append(errmsg)
                resp = self.form_invalid(form)
                # Revert the transaction: we don't want to save the ADS if we can't save the users.
                transaction.set_rollback(True)
                return resp

        if not self.request.POST.get(html_name_ads_legal_files_formset):
            ADSLegalFile.objects.filter(ads=self.object).delete()
        else:
            self.ads_legal_files_formset.instance = self.object
            self.ads_legal_files_formset.save()

        self.object.run_checks()

        messages.success(self.request, "Les modifications ont été enregistrées.")
        return HttpResponseRedirect(self.get_success_url())


def ads_manager_decree_view(request, manager_id):
    """Decree limiting the number of ADS for an ADSManager."""
    ads_manager = get_object_or_404(ADSManager, id=manager_id)

    if request.method == "POST":
        formset = ADSManagerDecreeFormSet(
            request.POST, request.FILES, instance=ads_manager
        )
        if formset.is_valid():
            formset.save()
            messages.success(request, "Les modifications ont été enregistrées.")
            return redirect("app.ads-manager.decree.detail", manager_id=manager_id)
    else:
        formset = ADSManagerDecreeFormSet(instance=ads_manager)

    return render(
        request,
        "pages/ads_register/ads_manager_decree.html",
        context={
            "ads_manager": ads_manager,
            "formset": formset,
        },
    )


class ADSDeleteView(DeleteView):
    template_name = "pages/ads_register/ads_confirm_delete.html"
    model = ADS
    pk_url_kwarg = "ads_id"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["ads_manager"] = ADSManager.objects.get(id=self.kwargs["manager_id"])
        return ctx

    def get_success_url(self):
        return reverse(
            "app.ads-manager.detail",
            kwargs={
                "manager_id": self.kwargs["manager_id"],
            },
        )


class ADSCreateView(ADSView, CreateView):
    def dispatch(self, request, manager_id):
        """If the ADSManager has the flag no_ads_declared to True, it is
        impossible to create ADS for it."""
        get_object_or_404(ADSManager, id=manager_id, no_ads_declared=False)

        html_name_ads_users_formset = (
            ADSUserFormSet().management_form["TOTAL_FORMS"].html_name
        )
        if self.request.POST.get(html_name_ads_users_formset):
            self.ads_users_formset = ADSUserFormSet(self.request.POST)
        else:
            self.ads_users_formset = ADSUserFormSet()
        self.ads_users_formset.extra = 1

        html_name_ads_legal_files_formset = (
            ADSLegalFileFormSet().management_form["TOTAL_FORMS"].html_name
        )
        if self.request.POST.get(html_name_ads_legal_files_formset):
            self.ads_legal_files_formset = ADSLegalFileFormSet(
                self.request.POST, self.request.FILES
            )
        else:
            self.ads_legal_files_formset = ADSLegalFileFormSet()
        return super().dispatch(request, manager_id)

    def get_object(self, queryset=None):
        return None

    def get_success_url(self):
        return reverse(
            "app.ads.detail",
            kwargs={"manager_id": self.kwargs["manager_id"], "ads_id": self.object.id},
        )

    def form_valid(self, form):
        ads_manager = ADSManager.objects.get(id=self.kwargs["manager_id"])
        form.instance.ads_manager = ads_manager

        # CreateView doesn't call validate_constraints(). The try/catch below
        # attemps to save the object. If IntegrityError is returned from
        # database, we return a custom error message for "number".
        try:
            with transaction.atomic():
                return super().form_valid(form)
        except IntegrityError:
            form.add_error("number", ADS.UNIQUE_ERROR_MSG)
            return super().form_invalid(form)


def prefecture_export_ads(request, ads_manager_administrator):
    prefecture = ads_manager_administrator.prefecture
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="ADS_prefecture_{prefecture.numero}.xlsx"'
        },
    )

    workbook = xlsxwriter.Workbook(response)
    bold_format = workbook.add_format({"bold": True})
    sheet1 = workbook.add_worksheet("ADS enregistrées")

    headers = (
        "Type d'administration",
        "Administration",
        "Numéro de l'ADS",
        "ADS actuellement exploitée ?",
        "Date de création de l'ADS",
        "Date du dernier renouvellement de l'ADS",
        "Date d'attribution de l'ADS au titulaire actuel",
        "Véhicule conventionné CPAM ?",
        "Plaque d'immatriculation du véhicule",
        "Le véhicule est-il un véhicule électrique/hybride ?",
        "Véhicule compatible PMR ?",
        "Titulaire de l'ADS",
        "SIRET du titulaire de l'ADS",
        "Téléphone fixe du titulaire de l'ADS",
        "Téléphone mobile du titulaire de l'ADS",
        "Email du titulaire de l'ADS",
    )
    # If one of the ADS in the list has, let's say, 4 drivers, driver_headers
    # will be appended 4 times to headers.
    driver_headers = (
        "Statut du %s conducteur",
        "Nom du %s conducteur",
        "SIRET du %s conducteur",
        "Numéro de la carte professionnelle du %s conducteur",
    )
    # Counts the maximum number of drivers in the list of ADS..
    max_drivers = 0

    # Applying bold format to headers
    sheet1.set_row(0, None, bold_format)

    def display_bool(value):
        if value is None:
            return ""
        return "oui" if value else "non"

    def display_date(value):
        if not value:
            return ""
        return value.strftime("%d/%m/%Y")

    for idx, ads in enumerate(
        ADS.objects.select_related(
            "ads_manager__administrator__prefecture",
        )
        .prefetch_related(
            "ads_manager__content_object",
        )
        .filter(ads_manager__administrator=ads_manager_administrator)
        .annotate(
            ads_users_status=ArrayAgg("adsuser__status"),
            ads_users_names=ArrayAgg("adsuser__name"),
            ads_users_sirets=ArrayAgg("adsuser__siret"),
            ads_users_licenses=ArrayAgg("adsuser__license_number"),
        )
    ):
        # Append driver headers to headers if the current ADS has more drivers
        # than the previous ones.
        while max_drivers < len(ads.ads_users_status):
            for h in driver_headers:
                headers += (
                    h % ("1er" if max_drivers == 0 else "%se" % (max_drivers + 1)),
                )
            max_drivers += 1

        info = (
            ads.ads_manager.content_object.type_name(),
            ads.ads_manager.content_object.text(),
            ads.number,
            display_bool(ads.ads_in_use),
            display_date(ads.ads_creation_date),
            display_date(ads.ads_renew_date),
            display_date(ads.attribution_date),
            display_bool(ads.accepted_cpam),
            ads.immatriculation_plate,
            display_bool(ads.eco_vehicle),
            display_bool(ads.vehicle_compatible_pmr),
            ads.owner_name,
            ads.owner_siret,
            ads.owner_phone,
            ads.owner_mobile,
            ads.owner_email,
        )
        for nth, status in enumerate(ads.ads_users_status):
            # ads_users_status, ads_users_names, ads_users_sirets and ads_users_licenses have the same length.
            info += (
                dict(ADSUser.status.field.choices).get(ads.ads_users_status[nth], ""),
                ads.ads_users_names[nth],
                ads.ads_users_sirets[nth],
                ads.ads_users_licenses[nth],
            )
        sheet1.write_row(idx + 1, 0, info)

    # Write headers, now that we know the maximum number of drivers.
    sheet1.write_row(0, 0, headers)
    sheet1.autofit()

    sheet2 = workbook.add_worksheet("Gestionnaires ADS")
    sheet2.write_row(
        0,
        0,
        (
            "Nom de l'administration",
            "Nombre d'ADS",
            "Statut de la gestion des ADS",
        ),
    )
    # Applying bold format to headers
    sheet2.set_row(0, None, bold_format)

    for idx, ads_manager in enumerate(ads_manager_administrator.adsmanager_set.all()):
        status = ""
        if ads_manager.no_ads_declared:
            status = "L'administration a déclaré ne gérer aucune ADS"
        elif ads_manager.epci_delegate:
            status = (
                "La gestion des ADS est déléguée à %s"
                % ads_manager.epci_delegate.display_fulltext()
            )

        sheet2.write_row(
            idx + 1,
            0,
            (
                ads_manager.content_object.display_text(),
                ads_manager.ads_set.count() or "",
                status,
            ),
        )
    sheet2.autofit()

    workbook.close()
    return response


class DashboardsView(TemplateView):
    template_name = "pages/ads_register/dashboards_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["stats"], ctx["stats_total"] = self.get_stats()
        return ctx

    def get_stats(self):
        """This function returns a tuple of two values:

        * stats: a list of dictionaries containing the following keys:
            - obj: the ADSManagerAdministrator instance
            - ads: a dictionary where keys represent the period (now, 3 months
              ago, 6 months ago, 12 months ago), and values are the number of ADS
              for this ADSManagerAdministrator
            - users: a dictionary where keys represent the period (now, 3 months
              ago, 6 months ago, 12 months ago), and values are the number of
              accounts who can create ADS for this ADSManagerAdministrator

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

        * stats_total: a dictionary containing the keys 'ads' and 'users', and
          the values are dictionaries where keys represent the period, and
          values are the total number of ADS and users.

        >>> {
        ...     'ads': {
        ...         'now': <int, total number of ADS currently registered>,
        ...         '3_months': <total number of ADS updated less than 3 months ago>,
        ...         '6_months': <total number of ADS updated less than 6 months ago>,
        ...         '12_months': <total number of ADS updated less than 12 months ago>,
        ...     },
        ...     'users': { ... }
        ... }
        """
        now = timezone.now()

        stats = collections.defaultdict(lambda: {"obj": None, "ads": {}, "users": {}})

        stats_total = {
            "ads": {},
            "users": {},
        }

        ads_query_now = (
            ADSManagerAdministrator.objects.select_related("prefecture")
            .annotate(ads_count=Count("adsmanager__ads"))
            .filter(ads_count__gt=0)
        )

        # All ADSManagerAdministrator, with the count of ADS with at least one of the contact fields filled.
        ads_with_info_query_now = (
            ADSManagerAdministrator.objects.select_related("prefecture")
            .annotate(
                ads_count=Count(
                    "adsmanager__ads",
                    filter=~Q(adsmanager__ads__owner_email="")
                    | ~Q(adsmanager__ads__owner_mobile="")
                    | ~Q(adsmanager__ads__owner_phone=""),
                )
            )
            .filter(ads_count__gt=0)
        )

        ads_query_3_months = (
            ADSManagerAdministrator.objects.select_related("prefecture")
            .filter(adsmanager__ads__creation_date__lte=now - timedelta(weeks=4 * 3))
            .annotate(ads_count=Count("adsmanager__ads"))
        )

        ads_query_6_months = (
            ADSManagerAdministrator.objects.select_related("prefecture")
            .filter(adsmanager__ads__creation_date__lte=now - timedelta(weeks=4 * 6))
            .annotate(ads_count=Count("adsmanager__ads"))
        )

        ads_query_12_months = (
            ADSManagerAdministrator.objects.select_related("prefecture")
            .filter(adsmanager__ads__creation_date__lte=now - timedelta(weeks=4 * 12))
            .annotate(ads_count=Count("adsmanager__ads"))
        )

        for label, query in (
            ("now", ads_query_now),
            ("with_info_now", ads_with_info_query_now),
            ("3_months", ads_query_3_months),
            ("6_months", ads_query_6_months),
            ("12_months", ads_query_12_months),
        ):
            for row in query:
                stats[row.prefecture.id]["obj"] = row
                stats[row.prefecture.id]["ads"][label] = row.ads_count

            stats_total["ads"][label] = query.aggregate(
                total=Coalesce(Sum("ads_count"), 0)
            )["total"]

        users_query_now = (
            ADSManagerAdministrator.objects.select_related("prefecture")
            .filter(adsmanager__adsmanagerrequest__accepted=True)
            .annotate(users_count=Count("id"))
        )

        users_query_3_months = (
            ADSManagerAdministrator.objects.select_related("prefecture")
            .filter(
                adsmanager__adsmanagerrequest__accepted=True,
                adsmanager__adsmanagerrequest__created_at__lte=now
                - timedelta(weeks=4 * 3),
            )
            .annotate(users_count=Count("id"))
        )

        users_query_6_months = (
            ADSManagerAdministrator.objects.select_related("prefecture")
            .filter(
                adsmanager__adsmanagerrequest__accepted=True,
                adsmanager__adsmanagerrequest__created_at__lte=now
                - timedelta(weeks=4 * 6),
            )
            .annotate(users_count=Count("id"))
        )

        users_query_12_months = (
            ADSManagerAdministrator.objects.select_related("prefecture")
            .filter(
                adsmanager__adsmanagerrequest__accepted=True,
                adsmanager__adsmanagerrequest__created_at__lte=now
                - timedelta(weeks=4 * 12),
            )
            .annotate(users_count=Count("id"))
        )

        for label, query in (
            ("now", users_query_now),
            ("3_months", users_query_3_months),
            ("6_months", users_query_6_months),
            ("12_months", users_query_12_months),
        ):
            for row in query.all():
                stats[row.prefecture.id]["obj"] = row
                stats[row.prefecture.id]["users"][label] = row.users_count

            stats_total["users"][label] = query.aggregate(
                total=Coalesce(Sum("users_count"), 0)
            )["total"]

        return (
            # Transform dict to an ordered list
            sorted(list(stats.values()), key=lambda stat: stat["obj"].id),
            stats_total,
        )


class DashboardsDetailView(DetailView):
    template_name = "pages/ads_register/dashboards_detail.html"
    model = ADSManagerAdministrator
    pk_url_kwarg = "ads_manager_administrator_id"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["stats"] = self.get_stats()
        return ctx

    def get_stats(self):
        stats = {}

        stats = collections.defaultdict(lambda: {"obj": None, "ads": {}, "users": {}})

        now = timezone.now()

        ads_query_now = (
            ADSManager.objects.prefetch_related("content_type", "content_object")
            .filter(administrator=self.object)
            .annotate(ads_count=Count("ads"))
            .filter(ads_count__gt=0)
        )

        # All ADSManager, with the count of ADS with at least one of the contact fields filled.
        ads_with_info_query_now = (
            ADSManager.objects.prefetch_related("content_type", "content_object")
            .filter(administrator=self.object)
            .annotate(
                ads_count=Count(
                    "ads",
                    filter=~Q(ads__owner_email="")
                    | ~Q(ads__owner_mobile="")
                    | ~Q(ads__owner_phone=""),
                )
            )
            .filter(ads_count__gt=0)
        )

        ads_query_3_months = (
            ADSManager.objects.prefetch_related("content_type", "content_object")
            .filter(
                administrator=self.object,
                ads__creation_date__lte=now - timedelta(weeks=4 * 3),
            )
            .annotate(ads_count=Count("ads"))
        )

        ads_query_6_months = (
            ADSManager.objects.prefetch_related("content_type", "content_object")
            .filter(
                administrator=self.object,
                ads__creation_date__lte=now - timedelta(weeks=4 * 6),
            )
            .annotate(ads_count=Count("ads"))
        )

        ads_query_12_months = (
            ADSManager.objects.prefetch_related("content_type", "content_object")
            .filter(
                administrator=self.object,
                ads__creation_date__lte=now - timedelta(weeks=4 * 12),
            )
            .annotate(ads_count=Count("ads"))
        )

        for label, query in (
            ("now", ads_query_now),
            ("with_info_now", ads_with_info_query_now),
            ("3_months", ads_query_3_months),
            ("6_months", ads_query_6_months),
            ("12_months", ads_query_12_months),
        ):
            for row in query:
                stats[row.id]["obj"] = row
                stats[row.id]["ads"][label] = row.ads_count

        users_query_now = (
            ADSManager.objects.prefetch_related("content_type", "content_object")
            .filter(administrator=self.object, adsmanagerrequest__accepted=True)
            .annotate(users_count=Count("id"))
        )

        users_query_3_months = (
            ADSManager.objects.prefetch_related("content_type", "content_object")
            .filter(
                administrator=self.object,
                adsmanagerrequest__accepted=True,
                adsmanagerrequest__created_at__lte=now - timedelta(weeks=4 * 3),
            )
            .annotate(users_count=Count("id"))
        )

        users_query_6_months = (
            ADSManager.objects.prefetch_related("content_type", "content_object")
            .filter(
                administrator=self.object,
                adsmanagerrequest__accepted=True,
                adsmanagerrequest__created_at__lte=now - timedelta(weeks=4 * 6),
            )
            .annotate(users_count=Count("id"))
        )

        users_query_12_months = (
            ADSManager.objects.prefetch_related("content_type", "content_object")
            .filter(
                administrator=self.object,
                adsmanagerrequest__accepted=True,
                adsmanagerrequest__created_at__lte=now - timedelta(weeks=4 * 12),
            )
            .annotate(users_count=Count("id"))
        )

        for label, query in (
            ("now", users_query_now),
            ("3_months", users_query_3_months),
            ("6_months", users_query_6_months),
            ("12_months", users_query_12_months),
        ):
            for row in query.all():
                stats[row.id]["obj"] = row
                stats[row.id]["users"][label] = row.users_count

        return sorted(list(stats.values()), key=lambda stat: stat["obj"].id)


class FAQView(TemplateView):
    template_name = "pages/faq.html"


class CustomCookieWizardView(CookieWizardView):
    def get_prefix(self, request, *args, **kwargs):
        """By default, WizardView uses the class name as a prefix. If the user
        opens several tabs at the same time, the storage is shared and weird
        behavior can happen.

        For example:

        * tab 1: from the page to create a decree for an ADS, go to second step
        * tab 2: from the page to create a decree for another ADS, go to second step
        * tab 2: refresh the page to go back to first step
        * tab 1: go to third step

        If the prefix is shared, an error will be raised because the form data
        have been deleted when the user refreshed the page in tab 2.

        We append the URL parameters to the prefix to avoid this issue most of
        the time. It is not perfect, but it is better than nothing. If the two
        tabs edit the same object, the prefix will be the same and the issue
        will still happen.
        """
        prefix = super().get_prefix(request, *args, **kwargs)
        suffix = "_".join(str(kwargs[key]) for key in sorted(kwargs.keys()))
        return f"{prefix}_{suffix}"

    def render_next_step(self, form, **kwargs):
        """The base class implementation of render_next_step has a bug, with the following scenario.

        Imagine a wizard with 3 steps.

        1. The user is at step 1, selects a field from a list, then goes to step 2
        2. The step 2 renders a select field with choices computed from the data
           of step 1. The user selects a value, and goes to step 3.
        3. The user goes back to step 2, then goes back to step 1.
        4. Finally, the user selects another value than the first time, and goes
           to step 2.

        Since the choices of the select field are computed from the data of step
        1, the choice previously select and stored refers to an invalid choice.

        To fix this issue, we delete the stored data of the next step before
        going to it.
        """
        if self.steps.next in self.storage.data[self.storage.step_data_key]:
            del self.storage.data[self.storage.step_data_key][self.steps.next]
        return super().render_next_step(form, **kwargs)

    def render_done(self, form, **kwargs):
        """The custom method render_done is called at the final step of the
        wizard. The base class resets the storage, which prevents to edit the
        form to regenerate the decree. We override the method to prevent the
        storage from being reset."""
        storage_reset = self.storage.reset
        self.storage.reset = lambda: None
        resp = super().render_done(form, **kwargs)
        self.storage.reset = storage_reset
        return resp


class ADSHistoryView(DetailView):
    template_name = "pages/ads_register/ads_history.html"
    model = ADS
    pk_url_kwarg = "ads_id"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["history"] = ModelHistory(
            self.object,
            ignore_fields=[
                ADS._meta.get_field("ads_manager"),
                ADS._meta.get_field("creation_date"),
                ADS._meta.get_field("last_update"),
                ADSLegalFile._meta.get_field("ads"),
                ADSLegalFile._meta.get_field("creation_date"),
                ADSUser._meta.get_field("ads"),
            ],
        )
        return ctx


class ADSDecreeView(CustomCookieWizardView):
    """Decree for ADS creation."""

    template_name = "pages/ads_register/ads_decree.html"
    form_list = (
        ADSDecreeForm1,
        ADSDecreeForm2,
        ADSDecreeForm3,
        ADSDecreeForm4,
    )

    def get_form_kwargs(self, step=None):
        """Instantiate ADSDecreeForm1 with the value of the previous form, to
        set the correct choices of the select field."""
        ret = super().get_form_kwargs(step=step)
        if step in ("1", "2"):
            return {"is_old_ads": self.get_cleaned_data_for_step("0").get("is_old_ads")}
        return ret

    def get_form_initial(self, step):
        """Set fields defaults."""
        ret = super().get_form_initial(step)
        ads = self.get_ads()

        if step == "0":
            ret.update(
                {
                    "is_old_ads": ads.ads_creation_date
                    and ads.ads_creation_date <= date(2014, 10, 1),
                }
            )
        elif step == "2":
            ads_user = ads.adsuser_set.first()

            now = datetime.now()
            try:
                today_in_5_years = now.replace(year=now.year + 5)
            except ValueError:  # 29th February
                today_in_5_years = now + timedelta(days=365 * 5)

            ret.update(
                {
                    "decree_creation_date": now.strftime("%Y-%m-%d"),
                    "decree_commune": ads.ads_manager.content_object.libelle,
                    "ads_owner": ads.owner_name,
                    # By default, we only display the first ADSUser. If there
                    # are more, user can edit the .docx generated manually.
                    "tenant_ads_user": ads_user.name if ads_user else "",
                    # New ADS have a validity of 5 years
                    "ads_end_date": today_in_5_years.strftime("%Y-%m-%d"),
                    "ads_number": ads.number,
                    "immatriculation_plate": ads.immatriculation_plate,
                }
            )
        return ret

    def get_ads(self):
        return get_object_or_404(
            ADS, id=self.kwargs["ads_id"], ads_manager_id=self.kwargs["manager_id"]
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["ads"] = self.get_ads()
        return ctx

    def done(self, form_list, **kwargs):
        path = finders.find("template-arrete-municipal.docx")
        decree = DocxTemplate(path)

        cleaned_data = self.get_all_cleaned_data()

        # DocxTemplate uses jinja2 to render the template. To render dates, we
        # could use {{ date.strftime(...)}} but the month would be in English.
        # Use the django date template filter to use correct format.
        cleaned_data.update(
            {
                k + "_str": date_template_filter(v, "d F Y")
                for k, v in cleaned_data.items()
                if isinstance(v, date)
            }
        )

        # Prefix the commune name with "la commune d'" or "la commune de "
        decree_commune = cleaned_data["decree_commune"]
        cleaned_data["decree_commune_fulltext"] = (
            "d'%s" % decree_commune
            if decree_commune[:1] in ("aeiouy")
            else "de %s" % decree_commune
        )

        decree.render(cleaned_data)

        response = HttpResponse(
            content_type="application/vnd.openxmlformats",
            headers={"Content-Disposition": 'attachment; filename="decret.docx"'},
        )

        decree.save(response)
        return response


class StatsView(TemplateView):
    template_name = "pages/stats.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx["ads_count"] = ADS.objects.count()

        ads_count_by_month = (
            ADS.objects.annotate(month=TruncMonth("creation_date"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )
        ctx["ads_count_by_month"] = json.dumps(
            dict(
                ((row["month"].isoformat(), row["count"]) for row in ads_count_by_month)
            )
        )

        ctx["ads_manager_requests_count"] = ADSManagerRequest.objects.filter(
            accepted=True
        ).count()

        ads_manager_requests_by_month = (
            ADSManagerRequest.objects.filter(accepted=True)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )
        ctx["ads_manager_requests_by_month"] = json.dumps(
            dict(
                (
                    (row["month"].isoformat(), row["count"])
                    for row in ads_manager_requests_by_month
                )
            )
        )

        ctx["ads_managers_count"] = (
            ADSManager.objects.annotate(ads_count=Count("ads"))
            .filter(ads_count__gt=0)
            .count()
        )

        return ctx


class ReglementationView(TemplateView):
    template_name = "pages/reglementation.html"
    entries = [
        {
            "title": "Principes généraux",
            "articles": [
                {
                    "title": "Le rôle des collectivités",
                    "template": "pages/reglementation/principes_generaux/role_collectivites.html",
                },
                {
                    "title": "Qu'est-ce qu'une ADS ?",
                    "template": "pages/reglementation/principes_generaux/qu_est_ce_qu_une_ads.html",
                },
                {
                    "title": "Qui délivre les ADS ?",
                    "template": "pages/reglementation/principes_generaux/qui_delivre_ads.html",
                },
            ],
        },
        {
            "title": "Délivrance d'une ADS",
            "articles": [
                {
                    "menu_title": "Arrêté délimitant le nombre d'ADS",
                    "title": "Étape 1 : l'arrêté délimitant le nombre d'ADS",
                    "template": "pages/reglementation/delivrance_ads/arrete_delimitant_ads.html",
                },
                {
                    "menu_title": "Attribution de l'ADS",
                    "title": "Étape 2 : l'attribution de l'ADS",
                    "template": "pages/reglementation/delivrance_ads/attribution_ads.html",
                },
                {
                    "menu_title": "L'arrêté municipal",
                    "title": "Étape 3 : la notification de l'arrêté",
                    "template": "pages/reglementation/delivrance_ads/notification_arrete.html",
                },
                {
                    "menu_title": "Retrait d'une ADS",
                    "title": "Étape 4 : le retrait d'une ADS",
                    "template": "pages/reglementation/delivrance_ads/retrait_ads.html",
                },
            ],
        },
        {
            "title": "Registre des taxis relais",
            "articles": [
                {
                    "title": "Qu'est-ce qu'un taxi relais ?",
                    "template": "pages/reglementation/relais/definition.html",
                },
            ],
        },
    ]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["entries"] = self.entries
        return ctx
