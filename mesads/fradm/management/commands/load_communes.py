import argparse
import csv
import sys

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from mesads.fradm.models import Commune


class Command(BaseCommand):
    help = 'Load communes from the CSV file published by INSEE (https://www.insee.fr/fr/information/5057840)'

    def add_arguments(self, parser):
        parser.add_argument('communes_file', type=argparse.FileType('r'))

    def handle(self, *args, **options):
        reader = csv.DictReader(options['communes_file'])

        with transaction.atomic():
            for row in reader:
                self.insert_row(row)

    def insert_row(self, row):
        if row['TYPECOM'] != 'COM':
            print(self.style.SUCCESS(
                '\nSkip insert of row of type %s: %s' % (row['TYPECOM'], row['NCC'])
            ))
            return

        # The get_or_create below might fail in future updates.
        # If we upload a Commune with COM=1234 and LIBELLE=xxx, then later
        # reimport with COM=1234 and LIBELLE=xxy: we will get an
        # IntegrityError. We need to find out why the data changed, and update
        # this loader accordingly.
        commune, created = Commune.objects.get_or_create(insee=row['COM'], libelle=row['LIBELLE'])
        sys.stdout.write(self.style.SUCCESS('.'))
        sys.stdout.flush()
