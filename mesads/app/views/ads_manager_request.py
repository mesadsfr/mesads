from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import OuterRef, Subquery, Count, IntegerField, BooleanField
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.generic.edit import FormView

from ..forms import (
    ADSManagerForm,
)
from ..models import (
    ADS,
    ADSManagerAdministrator,
    ADSManagerRequest,
    ADSUpdateLog,
)


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

        # All ADS for the manager
        ads_count_subquery = (
            ADS.objects.filter(
                ads_manager=OuterRef("ads_manager_id"),
                deleted_at__isnull=True,
            )
            .values("ads_manager")
            .annotate(count=Count("*"))
            .values("count")[:1]
        )

        # For each ADS, get its latest is_complete flag
        latest_complete = Subquery(
            ADSUpdateLog.objects.filter(ads=OuterRef("pk"))
            .order_by("-update_at")
            .values("is_complete")[:1],
            output_field=BooleanField(),
        )

        # 2) Count how many ADS under this manager have latest_complete=True
        complete_updates_subquery_per_ads_manager = Subquery(
            ADS.objects.filter(ads_manager=OuterRef("ads_manager_id"))
            .annotate(latest_complete=latest_complete)
            .filter(latest_complete=True)
            .values("ads_manager")
            .annotate(count=Count("pk"))
            .values("count")[:1],
            output_field=IntegerField(),
        )

        complete_ads_per_admin_per_ads_manager_administrator = Subquery(
            ADS.objects.filter(
                ads_manager__administrator=OuterRef("pk"),
                deleted_at__isnull=True,
            )
            .annotate(latest_complete=latest_complete)
            .filter(latest_complete=True)
            .values("ads_manager__administrator")
            .annotate(count=Count("pk"))
            .values("count")[:1],
            output_field=IntegerField(),
        )

        ctx["user_ads_manager_requests"] = ADSManagerRequest.objects.filter(
            user=self.request.user
        ).annotate(
            ads_count=Subquery(ads_count_subquery, output_field=IntegerField()),
            complete_updates_count=Subquery(
                complete_updates_subquery_per_ads_manager, output_field=IntegerField()
            ),
        )

        total_ads_per_ads_manager_admininistrator = Subquery(
            ADS.objects.filter(
                ads_manager__administrator=OuterRef("pk"),
                deleted_at__isnull=True,
            )
            .values("ads_manager__administrator")
            .annotate(count=Count("pk"))
            .values("count")[:1],
            output_field=IntegerField(),
        )

        ctx["ads_managers_administrators"] = (
            ADSManagerAdministrator.objects.select_related("prefecture")
            .filter(users=self.request.user)
            .annotate(
                ads_count=total_ads_per_ads_manager_admininistrator,
                complete_ads_count=complete_ads_per_admin_per_ads_manager_administrator,
            )
        )

        return ctx

    @transaction.atomic
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
                    notifications = getattr(administrator_user, "notification", None)
                    if not notifications or notifications.ads_manager_requests:
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
        return """
            Votre demande vient d'être envoyée à %(prefecture)s. Vous recevrez une confirmation de validation de votre
            accès par mail.<br /><br />

            En cas de difficulté ou si vous n'obtenez pas de validation de votre demande vous pouvez
            contacter par email à <a href="mailto:%(email)s">%(email)s</a> ou via notre module de tchat.<br /><br />

            Vous pouvez également demander un accès pour la gestion des ADS d'une autre collectivité.
        """ % {
            "prefecture": ads_manager.administrator.prefecture.display_fulltext(),
            "email": settings.MESADS_CONTACT_EMAIL,
        }
