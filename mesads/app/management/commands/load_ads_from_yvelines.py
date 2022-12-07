# XXX: this is a temporary script to load ads from Yvelines, it might be broken and will be removed soon

from datetime import date, datetime
import argparse
import csv
import re
import sys

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.contrib.postgres.lookups import Unaccent
from django.db.models import F, Value, Func, TextField

import dateparser

from mesads.app.models import ADS, ADSManager, ADSUser
from mesads.fradm.models import Commune


class Command(BaseCommand):
    help = (
        "Load ADS for Yvelines"
    )

    def add_arguments(self, parser):
        parser.add_argument('-f', '--ads-file', type=argparse.FileType('r'), required=True)

    def _log(self, level, msg):
        icon = (level == self.style.SUCCESS) and '✅' or '❌'

        sys.stdout.write(level(f'{icon} {msg}\n'))

    def find_commune(self, insee, libelle, departement):
        queries = [
            # Insee *and* libelle
            Commune.objects.filter(departement=departement, insee=insee, libelle__iexact=libelle),
            # Unaccent libelle
            Commune.objects.annotate(libelle_unaccent=Unaccent('libelle')).filter(
                departement=departement,
                libelle_unaccent__iexact=libelle
            ),
            # Replace common abbreviations to match what is in database, and ignore accents
            Commune.objects.annotate(
                libelle_unaccent=Unaccent('libelle')
            ).annotate(
                no_special_chars=Func(
                    F('libelle_unaccent'),
                    Value('[ \-]'),  # spaces
                    Value(''),  # replacement
                    Value('g'),  # regexp flags
                    function='REGEXP_REPLACE',
                )
            ).filter(
                departement=departement,
                no_special_chars__iexact=Unaccent(Value(libelle.lower()
                                                        .replace('st', 'saint')
                                                        .replace('/', 'sur')
                                                        .replace(' ', '')
                                                        .replace('-', '')
                                                        .replace('\n', '')))
            ),
        ]

        for query in queries:
            try:
                commune = query.get()
                return commune
            except Commune.DoesNotExist:
                continue
        return None

    def parse_date(self, value):
        if not value:
            return None

        parsed = dateparser.parse(value, languages=['fr'])
        if not parsed:
            return None
        return parsed.date()

    def parse_immatriculation_plate(self, value):
        for part in value.split():
            if re.match(r'([A-Z]{2,3}-)', part):
                return part

    def parse_siret(self, value):
        value = value.replace(' ', '')
        if re.match(r'[0-9]{14}', value):
            return value
        return None

    def parse_user_status(self, value):
        if not value:
            return None
        matches = {
            'titulaire': 'titulaire_exploitant',
            'propriétaire': 'titulaire_exploitant',
            'salarié': 'salarie',
            'locataire gérant': 'locataire_gerant',
            'locatire gérant': 'locataire_gerant',
            'locataire-gérant': 'locataire_gerant',
        }
        for m, replace in matches.items():
            if m.lower().replace(' ', '') in value.lower().replace(' ', ''):
                return replace
        return None

    def handle(self, ads_file, **opts):
        rows = csv.DictReader(ads_file)

        for line, row in enumerate(rows):
            line += 1
            row_commune = row['Nom de la commune']
            row_insee = row['Numéro INSEE de la commune ']

            # Hack to fix some data
            for csv_data, fixed_data in {
                'CONFLANS -ST-HONORINE.': 'Conflans-Sainte-Honorine',
                'BONNIERES': 'Bonnières-sur-Seine',
                'LE CHESNAY': 'Le Chesnay-Rocquencourt',
                'LE PERRAY': 'Le Perray-en-Yvelines',
                'Chesnay-Rocquencourt': 'Le Chesnay-Rocquencourt',
                'CLAIREFONTAINE': 'Clairefontaine-en-Yvelines',
                'LA QUEUE lez yves': 'La Queue-les-Yvelines',
                'FOLAINVILLE DENNEMONT': 'Follainville-Dennemont',
                'FOURQUEUX fusion avec ST GERMAIN EN LAYE': 'Saint-Germain-en-Laye',
                'ST LAMBERT DES BOIS': 'Saint-Lambert',
                'AUFREVILLE -BRASSEUIL': 'Auffreville-Brasseuil',
            }.items():
                if row_commune == csv_data:
                    row_commune = fixed_data

            commune = self.find_commune(row_insee, row_commune, '78')
            if not commune:
                self._log(self.style.ERROR, f'Line {line}: unknown commune: {row_commune}, ignore line')
                continue

            ads_manager = ADSManager.objects.filter(
                content_type=ContentType.objects.get_for_model(Commune),
                object_id=commune.id
            ).get()

            ads_number = row["Numéro de l'ADS"]
            if not ads_number:
                self._log(self.style.ERROR, f'Line {line}: skip entry without ADS number for {commune}')
                continue

            obj, created = ADS.objects.get_or_create(
                ads_manager=ads_manager,
                number=ads_number,
            )

            if created:
                self._log(self.style.SUCCESS, f'Line {line}: created ADS {ads_number} for {commune}')

            creation_date = row["Date de création de l'ADS"]
            parsed_creation_date = self.parse_date(creation_date)
            if creation_date and not parsed_creation_date:
                self._log(self.style.ERROR, f'Line {line}: unable to parse creation date: {creation_date}')
                continue

            obj.ads_creation_date = parsed_creation_date

            attribution_date = row["Date d'attribution de l'ADS"]
            parsed_attribuation_date = self.parse_date(attribution_date)
            if attribution_date and not parsed_attribuation_date:
                self._log(self.style.ERROR, f'Line {line}: unable to parse attribution date: {attribution_date}')
                continue
            obj.attribution_date = parsed_attribuation_date

            assert row["Type d'ADS"] in ('Ancienne', 'Nouvelle')
            obj.ads_type = 'old' if row["Type d'ADS"] == 'Ancienne' else 'new'

            if row["Type d'attribution"]:
                assert row["Type d'attribution"] in ('Payant', 'Gratuit')
                obj.attribution_type = 'paid' if row["Type d'attribution"] == 'Payant' else 'free'

            assert row["Raison de l'attribution"] in ("Création d'ADS", 'Néant', "Cession d'ADS", "Reprise d'ADS")
            obj.attribution_reason = "" if row["Raison de l'attribution"] == 'Néant' else row["Raison de l'attribution"]

            assert row["Conventionné CPAM"] in ('Oui', 'Non', 'Inconnu')
            if row["Conventionné CPAM"] == 'Oui':
                obj.accepted_cpam = True
            elif row["Conventionné CPAM"] == 'Non':
                obj.accepted_cpam = False

            immatriculation_plate = self.parse_immatriculation_plate(row["Plaque d'immatriculation véhicule"])
            if row["Plaque d'immatriculation véhicule"] and not immatriculation_plate:
                self._log(self.style.ERROR, f'Line {line}: unable to parse immatriculation plate: ' + row["Plaque d'immatriculation véhicule"])

            if immatriculation_plate:
                obj.immatriculation_plate = immatriculation_plate

            assert row["Véhicule PMR"] in ('Oui', 'Non', 'Inconnu')
            if row["Véhicule PMR"] == 'Oui':
                obj.vehicle_compatible_pmr = True
            elif row["Véhicule PMR"] == 'Non':
                obj.vehicle_compatible_pmr = False

            assert row["Véhicule électrique ou hybride"] in ('Oui', 'Non', 'Inconnu')
            if row["Véhicule électrique ou hybride"] == 'Oui':
                obj.eco_vehicle = True
            elif row["Véhicule électrique ou hybride"] == 'Non':
                obj.eco_vehicle = False

            owner_name = f'{row["Prénom du titulaire ADS"]} {row["Nom du titulaire ADS"]}'
            if row["Raison sociale du titulaire ADS"] and re.match(r'.*[a-z]', row["Raison sociale du titulaire ADS"]):
                owner_name += f' - {row["Raison sociale du titulaire ADS"]}'

            obj.owner_name = owner_name

            owner_siret = self.parse_siret(row["SIREN titulaire"])
            if row["SIREN titulaire"] and not owner_siret:
                self._log(self.style.ERROR, f'Line {line}: unable to parse owner SIRET: ' + row["SIREN titulaire"])
            if owner_siret:
                obj.owner_siret = owner_siret

            user_status = self.parse_user_status(row["Statut exploitant ADS (ancienne ADS)"])
            if row["Statut exploitant ADS (ancienne ADS)"] and not user_status:
                self._log(self.style.ERROR, f'Line {line}: unable to parse user status: ' + row["Statut exploitant ADS (ancienne ADS)"])

            user_name = f'{row["Prénom exploitant ADS"]} {row["Nom exploitant ADS"]}'
            user_siret = self.parse_siret(row["SIRET exploitant"])
            if row["SIRET exploitant"] and not user_siret:
                self._log(self.style.ERROR, f'Line {line}: unable to parse user SIRET: ' + row["SIRET exploitant"])

            user_license_number = (row['Numéro de carte professionnelle'])

            obj.save()

            if user_status or user_name or user_siret or user_license_number:
                ads_user, created = ADSUser.objects.get_or_create(
                    ads=obj
                )
                ads_user.status = user_status or ''
                ads_user.name = user_name or ''
                ads_user.siret = user_siret or ''
                ads_user.license_number = user_license_number or ''
                ads_user.save()
