from datetime import date, timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.db.models import DateField, ExpressionWrapper, F, Value
from django.template.loader import render_to_string

from mesads.app.models import ADSManager, ADSManagerRequest, InscriptionListeAttente


class Command(BaseCommand):
    help = (
        "Create ADSManager entries for Communes, EPCIs and Prefectures, "
        "create ADSManagerAdministrator entries and grant them permissions to "
        "ADSManager."
    )

    def handle(self, *args, **options):
        today = date.today()

        for ads_manager in (
            ADSManager.objects.prefetch_related(
                "adsmanagerrequest_set", "adsmanagerrequest_set__user"
            )
            .filter(adsmanagerrequest__accepted=True)
            .distinct()
        ):
            inscriptions = (
                InscriptionListeAttente.objects.filter(
                    ads_manager=ads_manager,
                    status=InscriptionListeAttente.ATTENTE_REPONSE,
                )
                .annotate(
                    date_limite=ExpressionWrapper(
                        F("date_contact")
                        + F("delai_reponse") * Value(timedelta(days=1)),
                        output_field=DateField(),
                    ),
                )
                .filter(date_limite=today - timedelta(days=1))
            )
            if inscriptions.count() > 0:
                ads_manager_requests = ADSManagerRequest.objects.filter(
                    ads_manager=ads_manager, accepted=True
                )
                emails = [
                    ads_manager_request.user.email
                    for ads_manager_request in ads_manager_requests
                ]

                email_subject = "Liste d'attente MesADS - Délai expiré"
                email_content = render_to_string(
                    "pages/email_liste_attente_delai_depasse.txt",
                    {
                        "inscriptions": inscriptions,
                        "ads_manager": ads_manager,
                        "base_url": settings.MESADS_BASE_URL,
                    },
                )
                email_content_html = render_to_string(
                    "pages/email_liste_attente_delai_depasse.mjml",
                    {
                        "inscriptions": inscriptions,
                        "ads_manager": ads_manager,
                        "base_url": settings.MESADS_BASE_URL,
                    },
                )
                send_mail(
                    email_subject,
                    email_content,
                    settings.MESADS_CONTACT_EMAIL,
                    emails,
                    fail_silently=True,
                    html_message=email_content_html,
                )
