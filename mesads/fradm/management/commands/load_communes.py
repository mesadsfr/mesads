import argparse
import csv
import sys

from django.core.management.base import BaseCommand
from django.db import transaction

from mesads.fradm.models import Commune


class Command(BaseCommand):
    help = "Load communes from the CSV file published by INSEE (https://www.insee.fr/fr/information/5057840)"

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
        if row["TYPECOM"] != "COM":
            print(
                self.style.SUCCESS(
                    "\nSkip insert of row of type %s: %s" % (row["TYPECOM"], row["NCC"])
                )
            )
            return 0

        # The get_or_create below might fail in future updates if we attempt to
        # reimport communes with different values for a row.
        # If IntegrityError is raised, we need to find out why data has changed
        # and change this loader accordingly.
        commune, created = Commune.objects.get_or_create(
            insee=row["COM"], departement=row["DEP"], libelle=row["LIBELLE"]
        )
        sys.stdout.write(self.style.SUCCESS("."))
        sys.stdout.flush()
        return int(created)
