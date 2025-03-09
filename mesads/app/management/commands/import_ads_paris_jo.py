import argparse
import csv
import datetime
import functools
import itertools
import re
import string
import sys
from unidecode import unidecode

import openpyxl

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from reversion.revisions import create_revision, set_user
from mesads.users.models import User

from mesads.app.models import ADS, ADSManager, ADSUser, validate_siret
from mesads.fradm.models import Commune, Prefecture


class Command(BaseCommand):
    help = "Import Paris / Jeux Olympiques file"

    def add_arguments(self, parser):
        parser.add_argument("-f", "--ads-file", required=True)

    def handle(self, ads_file, **kwargs):
        ads_manager = ADSManager.objects.filter(
            content_type=ContentType.objects.get_for_model(Prefecture),
            object_id=Prefecture.objects.filter(numero="75").get().id,
        ).get()
        try:
            # Remove ADSManager lock, otherwise ADS.save() will fail
            ads_manager.is_locked = False
            self.do_import(ads_manager, ads_file)
        finally:
            ads_manager.is_locked = True

    def do_import(self, ads_manager, ads_file):
        reader = csv.DictReader(open(ads_file, "r"), delimiter=";")

        for row in reader:
            numero = row["Numero d'ADS"]
            attribution = datetime.datetime.strptime(
                row["Date d'attribution"], "%d/%m/%Y"
            ).date()
            fin_attribution = row["Fin date d'attribution"]
            societe = row["Societe"]
            adresse = row["Adresse"]
            cp_ville = row["CP Ville"]
            tel_fixe = row["Tel fixe"]
            if tel_fixe:
                tel_fixe = "0" + tel_fixe
            tel_mobile = row["Tel mobile"]
            if tel_mobile:
                tel_mobile = "0" + tel_mobile
            email = row["Mail"]
            immatriculation = row["Immatriculation"]

            notes = f"""
Importé le {datetime.datetime.now()} depuis un fichier CSV fourni par la Préfecture de Police de Paris.
Adresse de la société : {adresse}, {cp_ville}
"""

            ADS.objects.create(
                ads_manager=ads_manager,
                number=numero,
                ads_in_use=True,
                ads_creation_date=attribution,
                owner_name=societe,
                owner_phone=tel_fixe,
                owner_mobile=tel_mobile,
                owner_email=email,
                immatriculation_plate=immatriculation,
                notes=notes.strip(),
            )
