from datetime import date, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import DateField, ExpressionWrapper, F, Value

from mesads.app.models import ADSManager, ADSManagerRequest, InscriptionListeAttente
from mesads.common.mail import envoi_email


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

                envoi_email(
                    content_template_txt="pages/email_liste_attente_delai_depasse.txt",
                    content_template_mjml="pages/email_liste_attente_delai_depasse.mjml",
                    context={
                        "inscriptions": inscriptions,
                        "ads_manager": ads_manager,
                        "base_url": settings.MESADS_BASE_URL,
                    },
                    destinataires=emails,
                    sujet="Liste d'attente MesADS - Délai expiré",
                )
