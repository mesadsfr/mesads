import argparse
import csv

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from mesads.app.models import ADSManager, ADSManagerAdministrator
from mesads.fradm.models import Commune, EPCI, Prefecture


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--expected-file', type=argparse.FileType('r'), required=True)

    def handle(self, expected_file, *args, **kwargs):
        reader = csv.reader(expected_file)
        for row in reader:
            departement = row[0]
            count = row[1]

            ads_manager_administrator = ADSManagerAdministrator.objects.filter(prefecture__numero=departement).get()
            ads_manager_administrator.expected_ads_count = count
            ads_manager_administrator.save()
