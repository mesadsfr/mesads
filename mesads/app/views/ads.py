from datetime import date, datetime, timedelta

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
    ADS_UNIQUE_ERROR_MESSAGE,
)
from ..reversion_diff import ModelHistory


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

        ctx["latest_ads_update_log"] = (
            ADSUpdateLog.objects.filter(
                ads=self.object,
            )
            .order_by("-update_at")
            .first()
        )
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
        ret = super().get_form_kwargs(step=step)
        if step in ("1", "2"):
            return {
                "is_old_ads": (self.get_cleaned_data_for_step("0") or {}).get(
                    "is_old_ads"
                )
            }
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
                ADSUpdateLog._meta.get_field("serialized"),
                ADSUpdateLog._meta.get_field("update_at"),
                ADSUpdateLog._meta.get_field("ads"),
                ADSLegalFile._meta.get_field("ads"),
                ADSLegalFile._meta.get_field("creation_date"),
                ADSUser._meta.get_field("ads"),
            ],
        )
        return ctx
