import argparse
import csv
import sys

from django.core.management.base import BaseCommand
from django.db import transaction

from mesads.fradm.models import EPCI


class Command(BaseCommand):
    help = """
        Création des EPCI depuis le fichier fourni par l'insee (https://www.insee.fr/fr/information/2510634)
        L'insee fournit un fichier excel, qu'il est nécessaire de modifier et convertir en csv, avec ";" comme delimiteur
    """

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
        # The get_or_create below might fail in future updates if we attempt to
        # reimport communes with different values for a row.
        # If IntegrityError is raised, we need to find out why data has changed
        # and change this loader accordingly.
        _, created = EPCI.objects.get_or_create(
            siren=row["EPCI"], departement=row["DEP"], name=row["LIBEPCI"]
        )
        sys.stdout.write(self.style.SUCCESS("."))
        sys.stdout.flush()
        return int(created)
