from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import date, timedelta
from mesads.app.models import InscriptionListeAttente, ADSManager
from faker import Faker


class Command(BaseCommand):
    help = (
        "Create ADSManager entries for Communes, EPCIs and Prefectures, "
        "create ADSManagerAdministrator entries and grant them permissions to "
        "ADSManager."
    )

    def handle(self, *args, **options):
        with transaction.atomic():
            manager_id = 73052
            ads_manager = ADSManager.objects.get(id=manager_id)
            f = Faker("fr_FR")

            inscriptions = []
            for i in range(0, 150):
                date_depot = f.date_between_dates(
                    date.today() - timedelta(days=400), date.today()
                )

                date_fin = date_depot + timedelta(days=365)
                inscriptions.append(
                    InscriptionListeAttente(
                        ads_manager=ads_manager,
                        numero=f"{i + 1}",
                        nom=f.last_name(),
                        prenom=f.first_name(),
                        numero_licence=f.bothify(
                            "????????", letters="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                        ),
                        numero_telephone=f.phone_number(),
                        email=f.ascii_safe_email(),
                        adresse=f.street_address(),
                        date_depot_inscription=date_depot,
                        date_dernier_renouvellement=date_depot,
                        date_fin_validite=date_fin,
                        commentaire="",
                        exploitation_ads=i % 3 == 0,
                    )
                )

            InscriptionListeAttente.objects.bulk_create(inscriptions)
