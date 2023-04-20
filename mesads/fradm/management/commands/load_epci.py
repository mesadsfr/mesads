import argparse
import csv
import sys

from django.core.management.base import BaseCommand
from django.db import transaction

from mesads.fradm.models import EPCI


class Command(BaseCommand):
    help = 'Load EPCI from the CSV file published by INSEE (https://www.insee.fr/fr/information/5057840). Insee only provides a .xlsx file, you will have to convert to CSV with ";" as delimiter before loading it.'

    def add_arguments(self, parser):
        parser.add_argument("epci_file", type=argparse.FileType("r"))

    def handle(self, *args, **options):
        reader = csv.DictReader(options["epci_file"], delimiter=";")
        created = 0
        with transaction.atomic():
            for row in reader:
                created += self.insert_row(row)
        print(self.style.SUCCESS(f"\nCreated: {created} new entries"))

    def insert_row(self, row):
        departement = row["dep_epci"]

        # The get_or_create below might fail in future updates if we attempt to
        # reimport communes with different values for a row.
        # If IntegrityError is raised, we need to find out why data has changed
        # and change this loader accordingly.
        epci, created = EPCI.objects.get_or_create(
            siren=row["siren_epci"], departement=departement, name=row["nom_complet"]
        )
        sys.stdout.write(self.style.SUCCESS("."))
        sys.stdout.flush()
        return int(created)
