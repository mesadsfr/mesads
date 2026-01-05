import csv
import re
import sys
from datetime import date, datetime

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from mesads.app.models import ADS, ADSManager, ADSUpdateFile
from mesads.fradm.models import Prefecture


class Logger:
    def __init__(self):
        self.history = []

    def log(self, level, msg):
        self.history.append(msg)
        # Avoid storing too many messages in memory.
        if len(self.history) > 100:
            self.history = self.history[-100:]

        sys.stdout.write(level(f"{msg}\n"))


class Command(BaseCommand):
    help = (
        "Every week, the Préfecture de Police de Paris publishes a CSV file with "
        "ADS updates. This command attempts to import the last file if it has not "
        "been already imported."
    )

    def handle(self, **opts):
        logger = Logger()

        ads_update_file = ADSUpdateFile.objects.order_by("-id").first()
        if not ads_update_file:
            logger.log(self.style.SUCCESS, "No file found, skip")
            return

        if ads_update_file.imported:
            logger.log(
                self.style.SUCCESS,
                (
                    f"ADSUpdateFile {ads_update_file.id} "
                    f"({ads_update_file.update_file.name}) "
                    "has already been imported, skip",
                ),
            )
            return

        ads_manager = ADSManager.objects.filter(
            content_type=ContentType.objects.get_for_model(Prefecture),
            object_id=Prefecture.objects.filter(numero="75").get().id,
        ).get()

        try:
            # Remove ADSManager lock, otherwise ADS.save() will fail
            ads_manager.is_locked = False
            self.do_import(ads_update_file, ads_manager, logger)
        finally:
            ads_manager.is_locked = True

    def do_import(self, ads_update_file, ads_manager, logger):
        logger.log(
            self.style.SUCCESS, f"Currently {ads_manager.ads_set.count()} ADS for Paris"
        )

        # The update file does not include the ADS created during the Jeux
        # Olympiques. Let's exclude them from this list. If we didnt' exclude
        # them, then they would be deleted below.
        all_paris_ads = {
            ads.number: ads
            for ads in ads_manager.ads_set.all()
            if not ads.number.startswith("JO")
        }

        new_count = 0
        update_count = 0
        with ads_update_file.update_file.storage.open(
            ads_update_file.update_file.name, "r"
        ) as handle:
            reader = csv.DictReader(handle.read().splitlines())

        for row in reader:
            import_ret = self.import_ads(ads_manager, all_paris_ads, row)
            if import_ret is None:  # did nothing
                continue
            elif import_ret:
                new_count += 1
            else:
                update_count += 1

        logger.log(
            self.style.SUCCESS,
            f"{new_count} new ADS imported, {update_count} ADS updated",
        )
        delete_count = 0
        for ads in all_paris_ads.values():
            if not getattr(ads, "_HAS_BEEN_UPDATED", False):
                delete_count += 1
                ads.delete()
        logger.log(self.style.SUCCESS, f"{delete_count} ADS deleted")

        ads_update_file.imported = True
        ads_update_file.import_output = "\n".join(logger.history)
        ads_update_file.save()

    def import_ads(self, ads_manager, all_paris_ads, row):
        # The last line of the CSV file only contains
        # one column with the number of rows.
        #  We skip it.
        if re.match(r"\(\d+ rows\)", row["numero_ads"]):
            return None

        ads = all_paris_ads.get(row["numero_ads"], None)
        is_new_object = False
        # Mark the object as updated,
        # so that we can delete the ones that are not in the file
        if ads:
            ads._HAS_BEEN_UPDATED = True
        else:
            ads = ADS(ads_manager=ads_manager, number=row["numero_ads"])
            is_new_object = True

        ads.ads_in_use = True

        if row["type_ads"] not in (
            "Payante",
            "Relais",
            "PMR",
            "Gratuite cessible",
            "Gratuite non cessible",
        ):
            raise ValueError(
                f'ADS {row["numero_ads"]}: invalid type_ads "{row["type_ads"]}"'
            )

        # The CSV file sent by Paris contains a field with the attribution date,
        # but not the creation date.
        # If "type" is "Gratuite non cessible", it's a new ADS and the date
        # should be considered as the creation date of the ADS.
        # If the type is anything else, it's an old ADS, this date is the
        # attribution date, and we don't have the creation date of the ADS, so
        # we hardcode it.
        attribution_date = datetime.strptime(row["date_attribution"], "%Y-%m-%d").date()

        if row["type_ads"] == "Gratuite non cessible":
            ads.ads_creation_date = attribution_date
            ads.attribution_date = None
        else:
            ads.ads_creation_date = date.min  # equals datetime.date(1, 1, 1)
            ads.attribution_date = attribution_date

        if row["type_ads"] == "PMR":
            ads.vehicle_compatible_pmr = True
        else:
            ads.vehicle_compatible_pmr = None
            if not ads.ads_creation_date or ads.ads_creation_date >= date(2014, 10, 1):
                ads.notes = ""
            else:
                ads.notes = f"Type d'ADS : {row['type_ads']}"

        ads.immatriculation_plate = row["immatriculation"]

        # https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000044084721
        if row["motorisation"].upper() in (
            "H2",
            "HH",
            "HE",
            "EL",
            "NE",
            "NH",
            "PE",
            "PH",
        ):
            ads.eco_vehicle = True
        else:
            ads.eco_vehicle = False

        if row["nom_artisan"]:
            ads.owner_name = f"{row['prenom_artisan']} {row['nom_artisan']}"
        else:
            ads.owner_name = row["nom_societe"]

        if row["num_siret"]:
            ads.owner_siret = row["num_siret"]

        if row["tel_fixe_titulaire"]:
            ads.owner_phone = row["tel_fixe_titulaire"]
        if row["tel_mobile_titulaire"]:
            ads.owner_mobile = row["tel_mobile_titulaire"]
        if row["adr_mail_titulaire"]:
            ads.owner_email = row["adr_mail_titulaire"]

        ads.save()
        return is_new_object
