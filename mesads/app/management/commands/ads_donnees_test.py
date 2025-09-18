from datetime import date
from faker import Faker

from django.db import transaction

from django.core.management.base import BaseCommand

from mesads.app.models import ADSManager, ADS, ADSUser


class Command(BaseCommand):
    help = ()

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch", type=int, default=1000, help="Managers par lot (défaut: 1000)"
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="N'écrit rien (test)"
        )

    def handle(self, *args, **options):
        BATCH_MANAGERS = options["batch"]
        dry_run = options["dry_run"]

        f = Faker("fr_FR")
        # Si tu veux des données reproductibles :
        # Faker.seed(1234)

        statuses = [
            "legal_representative",
            "salarie",
            "cooperateur",
            "locataire_gerant",
        ]

        managers_iter = (
            ADSManager.objects.order_by("id")
            .values_list("id", flat=True)
            .iterator(chunk_size=BATCH_MANAGERS)
        )

        batch_ids = []
        total_ads = 0
        total_users = 0
        processed_mgrs = 0

        def process_batch(ids):
            nonlocal total_ads, total_users, processed_mgrs
            if not ids:
                return

            # 1) Construire les ADS pour ce lot (en mémoire uniquement pour ce lot)
            ads_batch = []
            for mid in ids:
                # ADS "ancienne"
                ads1 = ADS(
                    number="1",
                    ads_manager_id=mid,
                    ads_creation_date=f.date_between_dates(
                        date(1990, 1, 1), date(2014, 1, 1)
                    ),
                    ads_in_use=True,
                    accepted_cpam=(mid % 3 == 0),
                    immatriculation_plate=f.license_plate(),
                    vehicle_compatible_pmr=(mid % 2 == 0),
                    eco_vehicle=(mid % 4 == 0),
                    owner_name=f"{f.last_name()} {f.first_name()}",
                    owner_siret="",
                    owner_phone=f.phone_number(),
                    owner_mobile=f.phone_number(),
                    # Évite f.unique.email() (mémoire) ; génère un email unique déterministe :
                    owner_email=f"owner-{mid}-old@example.com",
                )
                ads1.attribution_date = f.date_between_dates(
                    ads1.ads_creation_date, date.today()
                )
                ads_batch.append(ads1)

                # ADS "récente"
                ads2 = ADS(
                    number="2",
                    ads_manager_id=mid,
                    ads_creation_date=f.date_between_dates(
                        date(2015, 1, 1), date(2025, 1, 30)
                    ),
                    ads_in_use=True,
                    accepted_cpam=(mid % 3 == 0),
                    immatriculation_plate=f.license_plate(),
                    vehicle_compatible_pmr=(mid % 2 == 0),
                    eco_vehicle=(mid % 4 == 0),
                    owner_name=f"{f.last_name()} {f.first_name()}",
                    owner_siret="",
                    owner_phone=f.phone_number(),
                    owner_mobile=f.phone_number(),
                    owner_email=f"owner-{mid}-new@example.com",
                )
                ads2.ads_renew_date = f.date_between_dates(
                    ads2.ads_creation_date, date.today()
                )
                ads_batch.append(ads2)

            if dry_run:
                self.stdout.write(
                    self.style.WARNING(f"[DRY-RUN] Créer {len(ads_batch)} ADS")
                )
            else:
                # 2) Insert des ADS en lots
                # Ajoute batch_size si tu veux contrôler la taille par insert
                ADS.objects.bulk_create(ads_batch, batch_size=2000)
            total_ads += len(ads_batch)

            # 3) Récupérer les IDs des ADS créés pour ce lot (clé naturelle: (manager_id, number))
            created_ads = ADS.objects.filter(
                ads_manager_id__in=ids, number__in=["1", "2"]
            ).values("id", "ads_manager_id", "number")

            # 4) Construire les ADSUser du lot en s'appuyant sur ads_map
            users_batch = []
            for ads in created_ads:
                # 4 users pour ads1
                if ads["number"] == "1":
                    for idx, status in enumerate(statuses):
                        users_batch.append(
                            ADSUser(
                                ads_id=ads["id"],
                                status=status,
                                name=f"{f.last_name()} {f.first_name()}",
                                siret="",
                                license_number="123456",
                            )
                        )

                if ads["number"] == "2":
                    # 1 user pour ads2
                    users_batch.append(
                        ADSUser(
                            ads_id=ads["id"],
                            status="titulaire_exploitant",
                            name="",  # vide comme dans ta version
                            siret="",
                            license_number="123456",
                        )
                    )

            if dry_run:
                self.stdout.write(
                    self.style.WARNING(f"[DRY-RUN] Créer {len(users_batch)} ADSUser")
                )
            else:
                ADSUser.objects.bulk_create(users_batch, batch_size=5000)
            total_users += len(users_batch)

            processed_mgrs += len(ids)
            self.stdout.write(
                self.style.SUCCESS(
                    f"✔ Lot traité : {len(ids)} managers → {len(ads_batch)} ADS, {len(users_batch)} users "
                    f"(cumul: {processed_mgrs} managers, {total_ads} ADS, {total_users} users)"
                )
            )

        # Boucle principale : regroupe les ids par lots
        for mid in managers_iter:
            batch_ids.append(mid)
            if len(batch_ids) >= BATCH_MANAGERS:
                # Chaque lot dans sa propre transaction pour limiter la mémoire et la durée des verrous
                with transaction.atomic():
                    process_batch(batch_ids)
                batch_ids.clear()

        # Dernier lot partiel
        if batch_ids:
            with transaction.atomic():
                process_batch(batch_ids)

        self.stdout.write(self.style.SUCCESS("Terminé."))
