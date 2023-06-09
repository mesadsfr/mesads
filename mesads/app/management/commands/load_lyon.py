import argparse
import csv
import functools
import sys

from dateparser import parse

from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.lookups import Unaccent
from django.core.management.base import BaseCommand

from mesads.app.models import ADS, ADSManager, ADSUser, validate_siret
from mesads.fradm.models import Commune


class Command(BaseCommand):
    help = "Load ADS for Lyon"

    def add_arguments(self, parser):
        parser.add_argument(
            "-f",
            "--ads-file",
            type=argparse.FileType("r", encoding="utf-8-sig"),
            required=True,
        )

    def _log(self, level, msg, icon=None):
        if not icon:
            icon = (level == self.style.SUCCESS) and "✅" or "❌"
        sys.stdout.write(level(f"{icon} {msg}\n"))

    def handle(self, ads_file, **opts):
        rows = csv.DictReader(ads_file, delimiter=";")

        communes = {c.libelle: c for c in Commune.objects.filter(departement="69")}

        for row in rows:
            ads_id = row["ADS"]
            commune = self.find_commune(communes, row["COMMUNE"])
            ads_manager = self.get_ads_manager(commune.id)
            titulaire = " ".join(row["TITULAIRE"].split())
            last_attribution = parse(row["DATE DERNIERE ATTRIBUTION"]).date()
            license_plate = row["IMMATRICULATION"]
            eco_vehicle = self.is_eco_vehicle(row["ENERGIE"])

            ADS(
                number=ads_id,
                ads_manager=ads_manager,
                owner_name=titulaire,
                attribution_date=last_attribution,
                immatriculation_plate=license_plate,
                eco_vehicle=eco_vehicle,
            ).save()

    def find_commune(self, communes, name):
        for k, v in communes.items():
            if k.lower().replace(" ", "-").replace("é", "e") == name.lower().replace(
                " ", "-"
            ).replace("é", "e"):
                return v

        raise RuntimeError(f"Commune {name} not found")

    @functools.cache
    def get_ads_manager(self, commune_id):
        return ADSManager.objects.filter(
            content_type=ContentType.objects.get_for_model(Commune),
            object_id=commune_id,
        ).get()

    @functools.cache
    def is_eco_vehicle(self, energy):
        energy = energy.lower()
        if energy == "" or energy == "[vide]":
            return None
        if "hybride" in energy or "electrique" in energy:
            return True

        return False
