from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.generic import UpdateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, DeleteView

from reversion.views import RevisionMixin

from mesads.fradm.models import EPCI

from ..forms import (
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

    def build_formsets(self, ads):
        if self.request.method == "POST":
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
                f"{reverse('app.arretes-list', kwargs={'manager_id': ads_manager.id})}?ads_id={self.object.id}"
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

    def get_formsets(self):
        parent_instance = getattr(self, "object", None) or ADS()
        if self.request.method == "POST":
            ads_users_fs = ADSUserFormSet(self.request.POST, instance=parent_instance)
            ads_legal_files_fs = ADSLegalFileFormSet(
                self.request.POST, self.request.FILES, instance=parent_instance
            )
        else:
            ads_users_fs = ADSUserFormSet(instance=parent_instance)
            ads_legal_files_fs = ADSLegalFileFormSet(instance=parent_instance)
        return ads_users_fs, ads_legal_files_fs

    def dispatch(self, request, manager_id, **kwargs):
        """If the ADSManager has the flag no_ads_declared to True, it is
        impossible to create ADS for it."""
        get_object_or_404(ADSManager, id=manager_id, no_ads_declared=False)

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
                response = super().form_valid(form)
                if self.inscription:
                    self.inscription.ads_attribuee()
                return response
        except IntegrityError:
            form.add_error("number", ADS_UNIQUE_ERROR_MESSAGE)
            return super().form_invalid(form)


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
                ADSUpdateLog._meta.get_field("user"),
                ADSUpdateLog._meta.get_field("update_at"),
                ADSUpdateLog._meta.get_field("ads"),
                ADSLegalFile._meta.get_field("ads"),
                ADSLegalFile._meta.get_field("creation_date"),
                ADSUser._meta.get_field("ads"),
            ],
        )
        return context
