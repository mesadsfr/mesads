from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.generic.edit import FormView

from ..forms import (
    ADSManagerForm,
)
from ..models import (
    ADSManagerRequest,
)


class DemandeGestionADSView(FormView):
    template_name = "pages/ads_register/demande_gestion_ads.html"
    form_class = ADSManagerForm

    def get_success_url(self):
        return reverse("app.ads-manager.administrations")

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
            Vous avez déjà effectué une demande pour 
            gérer les ADS de %(administration)s. 
            Cette demande a été envoyée à %(prefecture)s qui devrait y 
            répondre rapidement.<br /><br />

            Si vous n'avez eu aucun retour depuis plusieurs jours, n'hésitez pas à 
            nous signaler le problème par email à 
            <a href="mailto:%(email)s">%(email)s</a>.
            <br /><br />
            Nous pourrons alors valider votre demande manuellement.
        """ % {
            "administration": ads_manager.content_object.display_fulltext(),
            "prefecture": ads_manager.administrator.prefecture.display_fulltext(),
            "email": settings.MESADS_CONTACT_EMAIL,
        }

    def get_message_for_new_request(self, ads_manager):
        return """
            Votre demande vient d'être envoyée à %(prefecture)s. 
            Vous recevrez une confirmation de validation de votre
            accès par mail.<br /><br />

            En cas de difficulté ou si vous n'obtenez pas de validation 
            de votre demande vous pouvez nous
            contacter par email à <a href="mailto:%(email)s">%(email)s</a>.<br /><br />

            Vous pouvez également demander un accès pour 
            la gestion des ADS d'une autre collectivité.
        """ % {
            "prefecture": ads_manager.administrator.prefecture.display_fulltext(),
            "email": settings.MESADS_CONTACT_EMAIL,
        }
