from datetime import date, datetime
import argparse
import csv
import sys

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from mesads.app.models import ADS, ADSManager, ADSUser, validate_siret
from mesads.fradm.models import Commune


class Command(BaseCommand):
    help = (
        "Load ADS for Metz"
    )

    def add_arguments(self, parser):
        parser.add_argument('-f', '--ads-file', type=argparse.FileType('r'), required=True)

    def _log(self, level, msg):
        sys.stdout.write(level(f'{msg}\n'))

    def handle(self, ads_file, **opts):
        ads_manager = ADSManager.objects.filter(
            content_type=ContentType.objects.get_for_model(Commune),
            object_id=Commune.objects.filter(insee='57463').get().id
        ).get()

        reader = csv.DictReader(ads_file, delimiter=';')

        for idx, row in enumerate(reader):
            print('...', idx + 1)
            self.add_ads(ads_manager, row)
        return

    def add_ads(self, ads_manager, row):
        assert row["Véhicule conventionné CPAM ?"] in ('OUI', 'Inconnu', 'NON', '', '? OUI ?')
        accepted_cpam = None
        if row["Véhicule conventionné CPAM ?"] == 'OUI':
            accepted_cpam = True
        elif row["Véhicule conventionné CPAM ?"] == 'NON':
            accepted_cpam = False

        assert row["Véhicule compatible PMR ?"] in ('Inconnu')
        assert row["Véhicule électrique ou hybride ?"] in ('Inconnu')

        owner_name = f'''{row["Prénom du titulaire de l'ADS"]} {row["Nom du titulaire de l'ADS"]}'''

        try:
            validate_siret(row["SIRET du titulaire de l'ADS"])
        except Exception as exc:
            print('Oops, error while validating', row["SIRET du titulaire de l'ADS"], exc)

        assert row["Téléphone fixe du titulaire de l'ADS"] == ''
        assert row["Téléphone mobile du titulaire de l'ADS"] == ''
        assert row["Email du titulaire de l'ADS"] == ''

        assert row["ADS exploitée par son titulaire ?"].lower() in ('oui', 'non')

        (ads, created) = ADS.objects.get_or_create(
            ads_manager=ads_manager,
            number=row["\ufeffNuméro de l'ADS"],
        )
        print(f'{ads} {"created" if created else "updated"}')

        ads.ads_creation_date = None  # not filled in CSV
        ads.attribution_date = datetime.strptime(
            row["Date d'attribution de l'ADS au titulaire actuel"],
            "%d/%m/%Y",
        ).date()
        ads.attribution_type = ''
        ads.transaction_identifier = ''
        ads.attribution_reason = ''
        ads.accepted_cpam = accepted_cpam
        ads.immatriculation_plate = row["Plaque d'immatriculation"]
        ads.vehicle_compatible_pmr = None
        ads.eco_vehicle = None
        ads.owner_name = owner_name
        ads.owner_siret = row["SIRET du titulaire de l'ADS"]
        ads.owner_phone = ''
        ads.owner_mobile = ''
        ads.owner_email = ''
        ads.used_by_owner = row["ADS exploitée par son titulaire ?"].lower() == 'oui'
        ads.save()

        assert row["Statut de l'exploitant de l'ADS"] in ('Titulaire exploitant', 'Locataire-gérant')
        if row["Statut de l'exploitant de l'ADS"] == 'Titulaire exploitant':
            ads_user_status = 'titulaire_exploitant'
        elif row["Statut de l'exploitant de l'ADS"] == 'Locataire-gérant':
            ads_user_status = 'locataire_gerant'

        ads_user_name = row["Nom de l'exploitant de l'ADS"]
        assert ads_user_name

        try:
            validate_siret(row["SIRET de l'exploitant de l'ADS"])
        except Exception as exc:
            print('Oops, error while validating', row["SIRET du titulaire de l'ADS"], exc)

        (ads_user, created) = ADSUser.objects.get_or_create(
            ads=ads
        )
        print(f'\tADSUser for {ads_user} {"created" if created else "updated"}')

        ads_user.status = ads_user_status
        ads_user.name = ads_user_name
        ads_user.siret = row["SIRET de l'exploitant de l'ADS"]
        ads_user.license_number = row["Numéro de la carte professionnelle"]
        ads_user.save()
