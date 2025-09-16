from datetime import date
from faker import Faker

from django.db import transaction

from django.core.management.base import BaseCommand

from mesads.app.models import ADSManager, ADS, ADSUser


class Command(BaseCommand):
    help = ()

    def handle(self, *args, **options):
        managers = ADSManager.objects.all()

        ads_to_create = []
        ads_users_to_create = []

        f = Faker("fr_FR")

        for manager in managers:
            # Creation ancienne ADS avec les 4 types de ADS Users possibles:
            ads_1 = ADS(
                number="1",
                ads_manager=manager,
                ads_creation_date=f.date_between_dates(
                    date(1990, 1, 1), date(2014, 1, 1)
                ),
                ads_in_use=True,
                accepted_cpam=manager.id % 3 == 0,
                immatriculation_plate=f.license_plate(),
                vehicle_compatible_pmr=manager.id % 2 == 0,
                eco_vehicle=manager.id % 4 == 0,
                owner_name=f"{f.last_name()} {f.first_name()}",
                owner_siret="",
                owner_phone=f.phone_number(),
                owner_mobile=f.phone_number(),
                owner_email=f.unique.email(),
            )
            ads_1.attribution_date = f.date_between_dates(
                ads_1.ads_creation_date, date.today()
            )
            ads_to_create.append(ads_1)

            for i in range(4):
                """
                Test test test
                """
                status = ""
                if i == 0:
                    status = "legal_representative"
                elif i == 1:
                    status = "salarie"
                elif i == 2:
                    status = "cooperateur"
                else:
                    status = "locataire_gerant"
                ads_user = ADSUser(
                    ads=ads_1,
                    status=status,
                    name=f"{f.last_name()} {f.first_name()}",
                    siret="",
                    license_number="123456",
                )
                ads_users_to_create.append(ads_user)

            # Creation d'une nouvelle ads avec le ads_user associé

            ads_2 = ADS(
                number="2",
                ads_manager=manager,
                ads_creation_date=f.date_between_dates(
                    date(2015, 1, 1), date(2025, 1, 30)
                ),
                ads_in_use=True,
                accepted_cpam=manager.id % 3 == 0,
                immatriculation_plate=f.license_plate(),
                vehicle_compatible_pmr=manager.id % 2 == 0,
                eco_vehicle=manager.id % 4 == 0,
                owner_name=f"{f.last_name()} {f.first_name()}",
                owner_siret="",
                owner_phone=f.phone_number(),
                owner_mobile=f.phone_number(),
                owner_email=f.unique.email(),
            )
            ads_2.ads_renew_date = f.date_between_dates(
                ads_2.ads_creation_date, date.today()
            )
            ads_to_create.append(ads_2)
            ads_user = ADSUser(
                ads=ads_2,
                status="titulaire_exploitant",
                name="",
                siret="",
                license_number="123456",
            )
            ads_users_to_create.append(ads_user)

        with transaction.atomic():
            ADS.objects.bulk_create(ads_to_create)
            ADSUser.objects.bulk_create(ads_users_to_create)
