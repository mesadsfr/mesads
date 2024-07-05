# When MesADS started, we loaded the commune published by INSEE from the file
# https://www.insee.fr/fr/information/5057840. We didn't insert all the rows
# that were not of type "COM".
# This script loads all the other types.

import argparse
import csv
import sys

from django.core.management.base import BaseCommand
from django.db import transaction

from mesads.fradm.models import Commune


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("communes_file", type=argparse.FileType("r"))

    def handle(self, *args, **options):
        reader = csv.DictReader(options["communes_file"])
        created = 0
        with transaction.atomic():
            for row in reader:
                created += self.insert_row(row)
        print(self.style.SUCCESS(f"\nCreated: {created} new entries"))

    def insert_row(self, row):
        if row["TYPECOM"] == "COM":
            return 0

        parent = Commune.objects.get(insee=row["COMPARENT"])

        if row["DEP"] != "" and row["DEP"] != parent.departement:
            raise ValueError("Departement mismatch")

        commune, created = Commune.objects.get_or_create(
            type_commune=row["TYPECOM"],
            insee=row["COM"],
            departement=parent.departement,
            libelle=row["LIBELLE"],
        )
        sys.stdout.write(self.style.SUCCESS("."))
        sys.stdout.flush()
        return int(created)
