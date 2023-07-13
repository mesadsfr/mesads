import argparse
import csv
import functools
import sys

from dateparser import parse

from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.lookups import Unaccent
from django.core.management.base import BaseCommand

from mesads.app.models import ADS, ADSManager, ADSUser, validate_siret
from mesads.fradm.models import Commune, EPCI


class Command(BaseCommand):
    help = "Fix ADS for lyon"

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

        epci_lyon = EPCI.objects.filter(name="Métropole de Lyon").get()
        ads_manager_epci = ADSManager.objects.filter(
            content_type=ContentType.objects.get_for_model(EPCI),
            object_id=epci_lyon.id,
        ).get()

        for row in rows:
            ads_id = row["ADS"]
            commune = self.find_commune(communes, row["COMMUNE"])

            try:
                ads = ADS.objects.get(number=ads_id, ads_manager__object_id=commune.id)
            except:
                ads = ADS.objects.get(number=ads_id, epci_commune_id=commune.id)
            ads.epci_commune = commune
            ads.ads_manager = ads_manager_epci
            ads.number = f"{commune.libelle} - {ads.number}"
            ads.save()

    def find_commune(self, communes, name):
        for k, v in communes.items():
            if k.lower().replace(" ", "-").replace("é", "e") == name.lower().replace(
                " ", "-"
            ).replace("é", "e"):
                return v

        raise RuntimeError(f"Commune {name} not found")
