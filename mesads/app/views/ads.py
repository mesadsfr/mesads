from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from docxtpl import DocxTemplate

from django.conf import settings
from django.contrib import messages
from django.contrib.staticfiles import finders
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import date as date_template_filter
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.generic import UpdateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, DeleteView

from formtools.wizard.views import CookieWizardView

from reversion.views import RevisionMixin

from mesads.fradm.models import EPCI

from ..forms import (
    ADSDecreeForm1,
    ADSDecreeForm2,
    ADSDecreeForm3,
    ADSDecreeForm4,
    ADSForm,
    ADSLegalFileFormSet,
    ADSUserFormSet,
)
from ..models import (
    ADS,
    ADSLegalFile,
    ADSManager,
    ADSUser,
    ADSUpdateLog,
    InscriptionListeAttente,
    ADS_UNIQUE_ERROR_MESSAGE,
)
from ..reversion_diff import ModelHistory


class ADSView(RevisionMixin, UpdateView):
    template_name = "pages/ads_register/ads.html"
    form_class = ADSForm
    inscription = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.inscription = None
        if request.GET.get("inscription_id"):
            self.inscription = get_object_or_404(
                InscriptionListeAttente, id=request.GET.get("inscription_id")
            )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        # If manager_id is the primary key of an EPCI, initialize ADSForm with
        # the parameter "epci" which is required to setup autocompletion for the
        # field ADS.epci_commune. This field is not displayed if the manager is
        # a Prefecture or a Commune.
        ads_manager = get_object_or_404(ADSManager, id=self.kwargs["manager_id"])
        if ads_manager.content_type.model_class() is EPCI:
            kwargs["epci"] = ads_manager.content_object

        if self.inscription:
            initial = kwargs.get("initial", {})
            initial.update(
                {
                    "owner_name": f"{self.inscription.nom} {self.inscription.prenom}",
                    "owner_phone": self.inscription.numero_telephone,
                    "owner_email": self.inscription.email,
                    "owner_siret": "",
                    "owner_mobile": "",
                    "accepted_cpam": None,
                    "immatriculation_plate": "",
                    "vehicle_compatible_pmr": None,
                    "eco_vehicle": None,
                }
            )
            kwargs["initial"] = initial

        return kwargs

    def _users_initial_from_inscription(self):
        if not self.inscription:
            return None
        return [
            {
                "license_number": self.inscription.numero_licence,
            }
        ]

    def build_formsets(self, ads):
        if self.request.method == "POST":
            if self.inscription:
                users_qs = ADSUser.objects.none()
            else:
                users_qs = ADSUser.objects.filter(ads=ads)

            ads_users_fs = ADSUserFormSet(
                self.request.POST,
                instance=ads,
                queryset=users_qs,
            )
            ads_legal_files_fs = ADSLegalFileFormSet(
                self.request.POST, self.request.FILES, instance=ads
            )
            if not ads.adsuser_set.count():
                ads_users_fs.extra = 1

        else:
            if self.inscription:
                initial_users = self._users_initial_from_inscription()
                ads_users_fs = ADSUserFormSet(
                    instance=ads,
                    queryset=ADSUser.objects.none(),  # n’affiche pas les existants
                    initial=initial_users,
                )
                ads_users_fs.extra = 1
            else:
                ads_users_fs = ADSUserFormSet(instance=ads)

            ads_legal_files_fs = ADSLegalFileFormSet(instance=ads)

        return ads_users_fs, ads_legal_files_fs

    def get_success_url(self):
        administrator = self.kwargs.get("ads_manager_administrator")
        return (
            reverse(
                "app.ads-manager-admin.ads-detail",
                kwargs={
                    "prefecture_id": administrator.prefecture.id,
                    "manager_id": self.kwargs["manager_id"],
                    "ads_id": self.kwargs["ads_id"],
                },
            )
            if administrator
            else reverse(
                "app.ads.detail",
                kwargs={
                    "manager_id": self.kwargs["manager_id"],
                    "ads_id": self.kwargs["ads_id"],
                },
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ads_manager"] = ADSManager.objects.get(id=self.kwargs["manager_id"])
        context["ads_users_formset"] = self.ads_users_formset
        context["ads_legal_files_formset"] = self.ads_legal_files_formset

        context["latest_ads_update_log"] = (
            ADSUpdateLog.objects.filter(
                ads=self.object,
            )
            .order_by("-update_at")
            .first()
        )
        administrator = self.kwargs.get("ads_manager_administrator")
        ads_manager = context["ads_manager"]
        if administrator:
            context["ads_manager_administrator"] = administrator
        context["return_url"] = (
            reverse(
                "app.ads-manager-admin.detail-administration",
                kwargs={
                    "prefecture_id": administrator.prefecture.id,
                    "manager_id": ads_manager.id,
                },
            )
            if administrator
            else reverse(
                "app.ads-manager.detail", kwargs={"manager_id": ads_manager.id}
            )
        )

        if self.object:
            context["arrete_url"] = (
                reverse(
                    "app.ads-manager-admin.ads-decree",
                    kwargs={
                        "prefecture_id": administrator.prefecture.id,
                        "manager_id": ads_manager.id,
                        "ads_id": self.object.id,
                    },
                )
                if administrator
                else reverse(
                    "app.ads.decree",
                    kwargs={"manager_id": ads_manager.id, "ads_id": self.object.id},
                )
            )
            context["history_url"] = (
                reverse(
                    "app.ads-manager-admin.ads-history",
                    kwargs={
                        "prefecture_id": administrator.prefecture.id,
                        "manager_id": ads_manager.id,
                        "ads_id": self.object.id,
                    },
                )
                if administrator
                else reverse(
                    "app.ads.history",
                    kwargs={"manager_id": ads_manager.id, "ads_id": self.object.id},
                )
            )

            context["delete_url"] = (
                reverse(
                    "app.ads-manager-admin.ads-delete",
                    kwargs={
                        "prefecture_id": administrator.prefecture.id,
                        "manager_id": ads_manager.id,
                        "ads_id": self.object.id,
                    },
                )
                if administrator
                else reverse(
                    "app.ads.delete",
                    kwargs={"manager_id": ads_manager.id, "ads_id": self.object.id},
                )
            )

        return context

    def get_object(self, queryset=None):
        ads = get_object_or_404(ADS, id=self.kwargs["ads_id"])
        self.ads_users_formset, self.ads_legal_files_formset = self.build_formsets(ads)
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
                    if self.inscription:
                        ADSUser.objects.filter(ads=self.object).delete()
                        self.ads_users_formset.save()
                    else:
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

        ADSUpdateLog.create_for_ads(self.object, self.request.user)

        for user in self.object.ads_manager.administrator.users.all():
            notification = getattr(user, "notification", None)
            if notification and notification.ads_created_or_updated:
                assert self.request.resolver_match.url_name in (
                    "app.ads.detail",
                    "app.ads.create",
                )
                self.send_notification(
                    user,
                    self.object,
                    self.request.resolver_match.url_name == "app.ads.create",
                )

        messages.success(self.request, "Les modifications ont été enregistrées.")
        return HttpResponseRedirect(self.get_success_url())

    def send_notification(self, user, ads, is_new_ads):
        email_subject = render_to_string(
            "pages/email_ads_created_or_updated_subject.txt",
            {
                "user": self.request.user,
                "ads": ads,
                "is_new_ads": is_new_ads,
            },
            request=self.request,
        ).strip()
        email_content = render_to_string(
            "pages/email_ads_created_or_updated_content.txt",
            {
                "user": self.request.user,
                "ads": ads,
                "is_new_ads": is_new_ads,
            },
            request=self.request,
        )
        email_content_html = render_to_string(
            "pages/email_ads_created_or_updated_content.mjml",
            {
                "user": self.request.user,
                "ads": ads,
                "is_new_ads": is_new_ads,
            },
            request=self.request,
        )
        send_mail(
            email_subject,
            email_content,
            settings.MESADS_CONTACT_EMAIL,
            [user.email],
            fail_silently=True,
            html_message=email_content_html,
        )


class ADSDeleteView(DeleteView):
    template_name = "pages/ads_register/ads_confirm_delete.html"
    model = ADS
    pk_url_kwarg = "ads_id"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ads_manager"] = ADSManager.objects.get(id=self.kwargs["manager_id"])
        return context

    def get_success_url(self):
        administrator = self.kwargs.get("ads_manager_administrator")
        return (
            reverse(
                "app.ads-manager-admin.detail-administration",
                kwargs={
                    "prefecture_id": administrator.prefecture.id,
                    "manager_id": self.kwargs["manager_id"],
                },
            )
            if administrator
            else reverse(
                "app.ads-manager.detail",
                kwargs={
                    "manager_id": self.kwargs["manager_id"],
                },
            )
        )


class ADSCreateView(ADSView, CreateView):
    inscription = None

    def get_initial(self):
        if self.inscription:
            return {
                "ads_creation_date": date.today(),
                "ads_in_use": True,
                "owner_name": f"{self.inscription.nom} {self.inscription.prenom}",
                "owner_phone": self.inscription.numero_telephone,
                "owner_email": self.inscription.email,
            }
        else:
            return super().get_initial()

    def _ads_users_initial_from_inscription(self):
        if not self.inscription:
            return None
        return [
            {
                "license_number": self.inscription.numero_licence,
            }
        ]

    def get_formsets(self):
        parent_instance = getattr(self, "object", None) or ADS()
        if self.request.method == "POST":
            ads_users_fs = ADSUserFormSet(self.request.POST, instance=parent_instance)
            ads_legal_files_fs = ADSLegalFileFormSet(
                self.request.POST, self.request.FILES, instance=parent_instance
            )
        else:
            initial_users = self._ads_users_initial_from_inscription()
            ads_users_fs = ADSUserFormSet(
                initial=initial_users, instance=parent_instance
            )
            ads_legal_files_fs = ADSLegalFileFormSet(instance=parent_instance)
        return ads_users_fs, ads_legal_files_fs

    def dispatch(self, request, manager_id, **kwargs):
        """If the ADSManager has the flag no_ads_declared to True, it is
        impossible to create ADS for it."""
        get_object_or_404(ADSManager, id=manager_id, no_ads_declared=False)

        if self.request.GET.get("inscription_id"):
            self.inscription = get_object_or_404(
                InscriptionListeAttente, id=self.request.GET.get("inscription_id")
            )
        self.ads_users_formset, self.ads_legal_files_formset = self.get_formsets()
        self.ads_users_formset.extra = 1
        return super().dispatch(request, manager_id, **kwargs)

    def get_object(self, queryset=None):
        return None

    def get_success_url(self):
        administrator = self.kwargs.get("ads_manager_administrator")
        return (
            reverse(
                "app.ads-manager-admin.ads-detail",
                kwargs={
                    "prefecture_id": administrator.prefecture.id,
                    "manager_id": self.kwargs["manager_id"],
                    "ads_id": self.object.id,
                },
            )
            if administrator
            else reverse(
                "app.ads.detail",
                kwargs={
                    "manager_id": self.kwargs["manager_id"],
                    "ads_id": self.object.id,
                },
            )
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
            form.add_error("number", ADS_UNIQUE_ERROR_MESSAGE)
            return super().form_invalid(form)


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
        suffix = "_".join(
            (
                str(kwargs[key].prefecture.id)
                if key == "ads_manager_administrator"
                else str(kwargs[key])
            )
            for key in sorted(kwargs.keys())
        )
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
        1, the choice previously selected and stored refers to an invalid choice.

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


class ADSDecreeMixin(CustomCookieWizardView):
    template_name = "pages/ads_register/ads_decree.html"
    form_list = (
        ADSDecreeForm1,
        ADSDecreeForm2,
        ADSDecreeForm3,
        ADSDecreeForm4,
    )

    def get_form_kwargs(self, step=None):
        form_kwargs = super().get_form_kwargs(step=step)
        if step in ("1", "2"):
            return {
                "is_old_ads": (self.get_cleaned_data_for_step("0") or {}).get(
                    "is_old_ads"
                )
            }
        return form_kwargs

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
            headers={"Content-Disposition": 'attachment; filename="arrete.docx"'},
        )

        decree.save(response)
        return response


class ADSDecreeView(ADSDecreeMixin):
    """Decree for ADS creation."""

    template_name = "pages/ads_register/ads_decree.html"
    form_list = (
        ADSDecreeForm1,
        ADSDecreeForm2,
        ADSDecreeForm3,
        ADSDecreeForm4,
    )

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
        context = super().get_context_data(**kwargs)
        context["ads"] = self.get_ads()

        administrator = self.kwargs.get("ads_manager_administrator")
        if administrator:
            context["ads_manager_administrator"] = administrator
        return context


class ADSDecreeEmptyView(ADSDecreeMixin):
    """Decree for ADS creation."""

    template_name = "pages/ads_register/ads_decree.html"
    form_list = (
        ADSDecreeForm1,
        ADSDecreeForm2,
        ADSDecreeForm3,
        ADSDecreeForm4,
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.kwargs.get("manager_id"):
            context["ads_manager"] = get_object_or_404(
                ADSManager, id=self.kwargs["manager_id"]
            )
        return context

    def get_form_initial(self, step):
        """Set fields defaults."""
        initial = super().get_form_initial(step)

        if step == "2":

            now = datetime.now()
            try:
                today_in_5_years = now + relativedelta(years=5)
            except ValueError:  # 29th February
                today_in_5_years = now + timedelta(days=365 * 5)

            initial.update(
                {
                    "decree_creation_date": now.strftime("%Y-%m-%d"),
                    # New ADS have a validity of 5 years
                    "ads_end_date": today_in_5_years.strftime("%Y-%m-%d"),
                }
            )
        return initial


class ADSHistoryView(DetailView):
    template_name = "pages/ads_register/ads_history.html"
    model = ADS
    pk_url_kwarg = "ads_id"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["history"] = ModelHistory(
            self.object,
            ignore_fields=[
                ADS._meta.get_field("ads_manager"),
                ADS._meta.get_field("creation_date"),
                ADS._meta.get_field("last_update"),
                ADSUpdateLog._meta.get_field("serialized"),
                ADSUpdateLog._meta.get_field("update_at"),
                ADSUpdateLog._meta.get_field("ads"),
                ADSLegalFile._meta.get_field("ads"),
                ADSLegalFile._meta.get_field("creation_date"),
                ADSUser._meta.get_field("ads"),
            ],
        )
        return context
