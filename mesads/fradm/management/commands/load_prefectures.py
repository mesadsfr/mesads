import argparse
import csv
import sys

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from mesads.fradm.models import Prefecture


class Command(BaseCommand):
    help = 'Load communes from the CSV file published by INSEE (https://www.insee.fr/fr/information/5057840)'

    def add_arguments(self, parser):
        parser.add_argument('prefectures_file', type=argparse.FileType('r'))

    def handle(self, *args, **options):
        reader = csv.DictReader(options['prefectures_file'])
        created = 0
        with transaction.atomic():
            for row in reader:
                created += self.insert_row(row)
        print(self.style.SUCCESS(f'\nCreated: {created} new entries'))

    def insert_row(self, row):
        # The get_or_create below might fail in future updates.
        # If we upload a Prefecture with DEP=1234 and LIBELLE=xxx, then later
        # reimport with DEP=1234 and LIBELLE=xxy: we will get an
        # IntegrityError. We need to find out why the data changed, and update
        # this loader accordingly.
        libelle = row['LIBELLE']

        if row['DEP'] == '75':
            libelle = 'Préfecture de Police de Paris'

        commune, created = Prefecture.objects.get_or_create(
            numero=row['DEP'], libelle=libelle
        )
        sys.stdout.write(self.style.SUCCESS('.'))
        sys.stdout.flush()
        return int(created)
