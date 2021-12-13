import argparse
import csv
from datetime import datetime
import sys

from django.core.management.base import BaseCommand
from django.db import transaction

from mesads.app.models import ADS, ADSManager
from mesads.fradm.models import Commune


class CSV_COLNAMES:
    """Mapping between fields and columns in CSV file exported by demarches-simplifiees."""
    insee = "Établissement code INSEE localité"
    ads_number = "Indiquer le numéro d’identification de l'ADS dans votre commune, EPCI ou préfecture"
    ads_creation_date = "Indiquer la date de création initiale de l’ADS"
    attribution_date = "Indiquer la date d’attribution de l’ADS au titulaire actuel"
    attribution_type = "Indiquer le mode d'obtention de l'ADS par le titulaire actuel"
    attribution_reason = "Si Autre, précisez le mode d'obtention"
    accepted_cpam = "Indiquer si l'autorisation de stationnement exploitée est conventionnée par l'Assurance Maladie"
    licence_plate = "Indiquer le numéro d'immatriculation du véhicule de taxi"
    pmr = "Indiquer si le véhicule est équipé pour le transport de personnes à mobilité réduite (PMR)"


class Command(BaseCommand):
    help = (
        "Load ADS for Ille et Vilaine from CSV file exported by demarches-simplfiees."
    )

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=argparse.FileType('r'))

    def handle(self, *args, **options):
        reader = csv.DictReader(options['csv_file'])
        with transaction.atomic():
            for row in reader:
                commune = Commune.objects.filter(insee=row[CSV_COLNAMES.insee]).get()

                # Our database models support a many to many relationship
                # between ADSManager and Commune, but in reality there is only
                # one manager for a given Commune.
                #
                # If this line raises, it means there is more than one manager
                # for the commune and we need a way to find which one should be
                # linked to the ADS created below.
                manager = commune.ads_managers.get()

                self.create_ads_for(row, manager)

    def _parse_date(self, value):
        """Parse %Y-%m-%d date, or return None."""
        if not value:
            return None
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            sys.stdout.write(self.style.WARNING(f'Date {value} with invalid format ignored, considered as None\n'))
            return None

    def _is_after(self, date_a, date_b):
        """Return True if date_a is after date_b."""
        if not date_a or not date_b:
            return False
        return date_a > date_b

    def _parse_attribution_type(self, row):
        """Parse column attribution_type."""
        value = row[CSV_COLNAMES.attribution_type]
        if value == "Cession à titre onéreux":
            return 'paid'
        elif value == "Gratuitement (délivrée par l'autorité compétente)":
            return "free"
        elif value == "Autre":
            return "other"
        raise ValueError(f"Invalid attribution type {value}")

    def _parse_accepted_cpam(self, row):
        value = row[CSV_COLNAMES.accepted_cpam].strip()
        if value.lower() == "oui":
            return True
        elif value.lower() == "non":
            return False
        elif value.lower() == "je ne sais pas":
            return None
        raise ValueError(f"Invalid CPAM value {value}")

    def _parse_pmr(self, row):
        value = row[CSV_COLNAMES.pmr].strip()
        if value.lower() == "oui":
            return True
        elif value.lower() == "non":
            return False
        elif value.lower() == "je ne sais pas":
            return None
        raise ValueError(f"Invalid PMR col {value}")

    def create_ads_for(self, row, manager):
        """Create or update ADS entry."""
        ads_number = row[CSV_COLNAMES.ads_number].strip()
        ads, created = ADS.objects.get_or_create(ads_manager=manager, number=ads_number)

        ads_creation_date = self._parse_date(row[CSV_COLNAMES.ads_creation_date])
        attribution_date = self._parse_date(row[CSV_COLNAMES.attribution_date])

        # Remove duplicates from database.
        if self._is_after(ads.ads_creation_date, ads_creation_date):
            sys.stdout.write(self.style.WARNING(
                f'ADS number {ads.number} for {manager} exists in database with '
                f'a creation date of {ads.ads_creation_date}. The CSV file '
                f'contains a row for this ADS with a creation date of '
                f'{ads_creation_date}. Since this row is older than the value in '
                f'database, it is ignored.\n'
            ))
            return

        if self._is_after(ads.attribution_date, attribution_date):
            sys.stdout.write(self.style.WARNING(
                f'ADS number {ads.number} for {manager} exists in database with '
                f'a attribution date of {ads.attribution_date}. The CSV file '
                f'contains a row for this ADS with an attribution date of '
                f'{attribution_date}. Since this row is older than the value in '
                f'database, it is ignored.\n'
            ))
            return

        ads.ads_creation_date = ads_creation_date
        ads.attribution_date = attribution_date
        ads.attribution_type = self._parse_attribution_type(row)
        ads.attribution_reason = row[CSV_COLNAMES.attribution_reason]
        ads.accepted_cpam = self._parse_accepted_cpam(row)
        ads.immatriculation_plate = row[CSV_COLNAMES.licence_plate]
        ads.vehicle_compatible_pmr = self._parse_pmr(row)

        ads.save()
