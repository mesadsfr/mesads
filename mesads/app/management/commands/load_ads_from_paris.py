# XXX: this is a temporary script to load ads from Paris, it might be broken

from datetime import date, datetime
import argparse
import csv
import sys

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from mesads.app.models import ADS, ADSManager
from mesads.fradm.models import Prefecture


class Command(BaseCommand):
    help = (
        "Load ADS for Paris"
    )

    def add_arguments(self, parser):
        parser.add_argument('-f', '--ads-file', type=argparse.FileType('r'), required=True)

    def _log(self, level, msg):
        sys.stdout.write(level(f'{msg}\n'))

    def handle(self, ads_file, **opts):
        ads_manager = ADSManager.objects.filter(
            content_type=ContentType.objects.get_for_model(Prefecture),
            object_id=Prefecture.objects.filter(numero='75').get().id
        ).get()

        reader = csv.DictReader(ads_file, delimiter=';')

        for row in reader:
            params = {}

            params['attribution_date'] = datetime.strptime(
                row['date_attribution'],
                '%Y-%m-%d'
            ).date()

            # The date is not provided in the CSV file. For new ADS, created
            # after October 1st 2014, the date is always equivalent to the
            # attribution date. For other types of ADS, we don't know.
            if params['attribution_date'] >= date(2014, 10, 1):
                params['ads_creation_date'] = params['attribution_date']
            else:
                params['ads_creation_date'] = None

            # Values of field "type_ads" is any of:
            # - Payante
            # - Relais
            # - PMR
            # - Gratuite cessible
            # - Gratuite non cessible
            # Fill the corresponding field accordingly
            assert row['type_ads'] in (
                'Payante',
                'Relais',
                'PMR',
                'Gratuite cessible',
                'Gratuite non cessible',
            ), 'Invalid type_ads in %s' % row

            if row['type_ads'] == 'PMR':
                params['vehicle_compatible_pmr'] = True
            elif row['type_ads'] == 'Payante':
                params['attribution_type'] = 'paid'
            elif row['type_ads'] in ('Gratuite cessible', 'Gratuite non cessible'):
                params['attribution_type'] = 'free'
            elif row['type_ads'] == 'Relais':
                params['attribution_reason'] = 'Relais'

            params['immatriculation_plate'] = row['immatriculation']

            # https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000044084721
            if row['motorisation'].upper() in (
                'H2', 'HH', 'HE', 'EL', 'NE', 'NH', 'PE', 'PH'
            ):
                params['eco_vehicle'] = True
            else:
                params['eco_vehicle'] = False

            if row['nom_artisan']:
                assert row['prenom_artisan'], 'Missing prenom_artisan in %s' % row
                params['owner_name'] = '%s %s' % (row['prenom_artisan'], row['nom_artisan'])
            else:
                assert row['nom_societe'], 'Missing nom_societe in %s' % row
                params['owner_name'] = row['nom_societe']

            if row['num_siret']:
                params['owner_siret'] = row['num_siret']

            if row['tel_fixe_titulaire']:
                params['owner_phone'] = row['tel_fixe_titulaire']
            if row['tel_mobile_titulaire']:
                params['owner_mobile'] = row['tel_mobile_titulaire']
            if row['adr_mail_titulaire']:
                params['owner_email'] = row['adr_mail_titulaire']

            ads, created = ADS.objects.update_or_create(
                number=row['numero_ads'], ads_manager=ads_manager,
                defaults=params
            )

            self._log(self.style.SUCCESS, f'ADS {ads.id} (number {ads.number}) {created and "created" or "updated"}')
