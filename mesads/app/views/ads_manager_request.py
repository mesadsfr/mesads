from django.conf import settings
from django.contrib import messages
from django.urls import reverse
from django.views.generic.edit import FormView

from mesads.common.mail import envoi_email

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

            emails = [
                user.email
                for user in form.cleaned_data["ads_manager"].administrator.users.all()
                if getattr(user, "notification", None) is None
                or getattr(user, "notification", None).ads_manager_requests
            ]

            envoi_email(
                content_template_txt="pages/email_ads_manager_request_administrator_content.txt",
                content_template_mjml="pages/email_ads_manager_request_administrator_content.mjml",
                context={
                    "request": self.request,
                    "ads_manager": form.cleaned_data["ads_manager"],
                    "user": self.request.user,
                },
                destinataires=emails,
                sujet_template="pages/email_ads_manager_request_administrator_subject.txt",
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
