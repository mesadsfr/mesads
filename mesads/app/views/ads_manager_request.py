from django.conf import settings
from django.contrib import messages
from django.core.exceptions import SuspiciousOperation
from django.core.mail import send_mail
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView
from django.views.generic.edit import FormView

from reversion.views import RevisionMixin

from ..forms import (
    ADSManagerForm,
)
from ..models import (
    ADSManagerAdministrator,
    ADSManagerRequest,
)


class ADSManagerAdminView(RevisionMixin, TemplateView):
    """This view is used by ADSManagerAdministartors to validate ADSManagerRequests."""

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
