import argparse
import csv
import sys

from django.core.management.base import BaseCommand
from django.db import transaction

from mesads.fradm.models import Commune


class Command(BaseCommand):
    help = "Création des communes via le csv fourni par l'INSEE (https://www.insee.fr/fr/information/5057840)"

    def add_arguments(self, parser):
        parser.add_argument("communes_file", type=argparse.FileType("r"))

    def handle(self, *args, **options):
        reader = csv.DictReader(options["communes_file"])
        created = 0

        communes_rows = []
        communes_autre_rows = []

        for row in reader:
            (communes_rows if row["TYPECOM"] == "COM" else communes_autre_rows).append(
                row
            )
        with transaction.atomic():
            for row in communes_rows:
                created += self.upsert_commune(row)
            for row in communes_autre_rows:
                created += self.upsert_commune_autre(row)
        print(self.style.SUCCESS(f"\nCreated: {created} new entries"))

    def upsert_commune(self, row):
        _, created = Commune.objects.get_or_create(
            type_commune=row["TYPECOM"],
            insee=row["COM"],
            departement=row["DEP"],
            libelle=row["LIBELLE"],
        )
        sys.stdout.write(self.style.SUCCESS("."))
        sys.stdout.flush()
        return int(created)

    def upsert_commune_autre(self, row):
        parent = Commune.objects.get(insee=row["COMPARENT"])

        if row["DEP"] != "" and row["DEP"] != parent.departement:
            raise ValueError("Departement mismatch")

        _, created = Commune.objects.get_or_create(
            type_commune=row["TYPECOM"],
            insee=row["COM"],
            departement=parent.departement,
            libelle=row["LIBELLE"],
        )
        sys.stdout.write(self.style.SUCCESS("."))
        sys.stdout.flush()
        return int(created)
