# XXX: this is a temporary script to load ads from Yvelines, it might be broken and will be removed soon

import argparse
import csv
import re
import sys

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from django.contrib.postgres.lookups import Unaccent
from django.db.models import F, Value, Func

import dateparser

from mesads.app.models import ADS, ADSManager, ADSUser, validate_siret
from mesads.fradm.models import Commune


class Command(BaseCommand):
    help = (
        "Load ADS for Yvelines"
    )

    def add_arguments(self, parser):
        parser.add_argument('-f', '--ads-file', type=argparse.FileType('r'), required=True)

    def _log(self, level, msg, icon=None):
        if not icon:
            icon = (level == self.style.SUCCESS) and '✅' or '❌'

        sys.stdout.write(level(f'{icon} {msg}\n'))

    def handle(self, ads_file, **opts):
        rows = csv.DictReader(ads_file)

        communes_query = Commune.objects.filter(libelle="Brest")
        assert communes_query.count() == 1
        ads_manager = ADSManager.objects.filter(
            content_type=ContentType.objects.get_for_model(Commune),
            object_id=communes_query.first().id
        ).get()

        for row in rows:
            ads_creation_date = dateparser.parse(row["Date de création de l'ADS"])

            ads_type = {
                '''L'ADS a été créée avant la loi du 1er Octobre 2014 : "ancienne ADS "''': 'old',
                '''L'ADS a été créée après la loi du 1er Octobre 2014 : "nouvelle ADS "''': 'new',
            }[row["Type d'ADS"]]

            if row["Date d'attribution de l'ADS au titulaire actuel"] == 'vente en cours':
                attribution_date = None
            else:
                attribution_date = dateparser.parse(row["Date d'attribution de l'ADS au titulaire actuel"]).date()

            attribution_type = {
                'Cession à titre onéreux': 'free',
                "Gratuitement (délivrée par l'autorité compétente)": 'paid'
            }[row["Type d'attribution de l'ADS"]]

            accepted_cpam = {
                'oui': True,
                'non': False,
                '': None,
            }[row['Véhicule conventionné CPAM ?'].strip()]

            immatriculation_plate = row["Plaque d'immatriculation"]
            if '-' in immatriculation_plate:
                immatriculation_plate = immatriculation_plate.replace(' ', '')
            else:
                immatriculation_plate = immatriculation_plate.strip().replace('  ', ' ').replace(' ', '-')

            vehicle_compatible_pmr = {
                'oui': True,
                'non': False,
                'non  mais prend des persones en fauteuil roulant': False,
                '': None,
                'hybride': None,
            }[row["Véhicule compatible PMR ?"].lower()]

            eco_vehicle = {
                'oui': True,
                'non': False,
                'hybride': True,
                'electrique': True,
                'électrique': True,
                'flexifluel': False,
                '': None,
            }[row["Véhicule électrique ou hybride ?"].lower()]

            owner_name = (re.sub(
                r' +',
                ' ',
                row["Nom du titulaire de l'ADS"].strip().replace('\n', ' ')
            ))

            owner_siret = re.sub(
                r'[^0-9]',
                '',
                row["SIRET du titulaire de l'ADS"]
            )
            # validate_siret(owner_siret)

            owner_phone = re.sub(
                r'[^\d]',
                '',
                row["Téléphone fixe du titulaire de l'ADS"].split('\n')[0]
            )

            owner_mobile = re.sub(
                r'[^\d]',
                '',
                row["Téléphone mobile du titulaire de l'ADS"].split('\n')[0]
            )

            owner_email = row["Email du titulaire de l'ADS"].strip()

            used_by_owner = {
                'oui': True,
                'non': False,
            }[row["ADS exploitée par son titulaire ?"]]

            (ads, created) = ADS.objects.get_or_create(
                ads_manager=ads_manager,
                number=row["Numéro de l'ADS"]
            )

            ads.ads_creation_date = ads_creation_date
            ads.ads_type = ads_type
            ads.attribution_date = attribution_date
            ads.attribution_type = attribution_type
            ads.accepted_cpam = accepted_cpam
            ads.immatriculation_plate = immatriculation_plate
            ads.vehicle_compatible_pmr = vehicle_compatible_pmr
            ads.eco_vehicle = eco_vehicle
            ads.owner_name = owner_name
            ads.owner_siret = owner_siret
            ads.owner_phone = owner_phone
            ads.owner_mobile = owner_mobile
            ads.owner_email = owner_email
            ads.used_by_owner = used_by_owner

            ads.save()

            if created:
                self._log(self.style.SUCCESS, f"ADS {ads.number} created")
            else:
                self._log(self.style.SUCCESS, f"ADS {ads.number} updated", icon="📝")

            # ADSUser.objects.filter(ads=ads).delete()

            for prefix in ('', '2e ', '3e '):
                user_status = {
                    '': '',
                    'Titulaire exploitant': 'titulaire_exploitant',
                    'Salarié': 'salarie',
                    'Locataire gérant': 'locataire_gerant',
                    'Co-gérant': '',
                }[row[f"{prefix}Statut de l'exploitant de l'ADS"]]
                user_name = (row[f"{prefix}Nom de l'exploitant de l'ADS"]).strip().replace('\n', ' ')

                user_siret = re.sub(
                    r'[^0-9]',
                    '',
                    row[f"{prefix}SIRET de l'exploitant de l'ADS"]
                )
                # validate_siret(user_siret)

                user_license_number = row[f"{prefix}Numéro de la carte professionnelle"]

                if not user_name:
                    continue

                (ads_user, created) = ADSUser.objects.get_or_create(
                    ads=ads,
                    name=user_name
                )
                ads_user.status = user_status
                ads_user.siret = user_siret
                ads_user.license_number = user_license_number

                ads_user.save()

                if created:
                    self._log(self.style.SUCCESS, f"\tADSUSer {ads_user.id} for \"{ads_user.name}\" created")
                else:
                    self._log(self.style.SUCCESS, f"\tADSUser {ads_user.id} for \"{ads_user.name}\" updated", icon="📝")
