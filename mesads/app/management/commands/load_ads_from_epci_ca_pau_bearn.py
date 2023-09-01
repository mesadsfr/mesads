import argparse
import csv
from datetime import datetime

from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.lookups import Unaccent
from django.core.management.base import BaseCommand

from mesads.app.models import ADS, ADSManager, validate_siret
from mesads.fradm.models import EPCI, Commune

COMMUNE = "\ufeffCOMMUNE DE RATTACHEMENT"
ADS_NUMBER = "N° ADS"
ADS_TYPE = "De quelle type d'ADS s'agit-il ?"
OWNER_DATE = "A quelle date êtes-vous devenu le titulaire actuel de l'ADS ?"
ATTRIBUTION_DATE = "Comment l'ADS vous a-t-elle été attribuée ?"
OWNER = "TITULAIRE DE L'ADS\n(personne physique inscrite au répertoire des métiers ou personne morale inscrite au registre du commerce et des sociétés)"
CPAM = "Disposez-vous d'un conventionnement avec la CPAM ?"
LICENSE_PLATE = (
    "Quelle est l'immatriculation du véhicule utilisé pour exploiter l'ADS ?"
)
PMR = "Votre véhicule est-il compatible PMR ?"
ECO_VEHICLE = "Votre véhicule est-il électrique ou hybride ?"
SIRET = "Quel est votre n° SIRET (14 chiffres)"
PHONE = "Quel est votre n° de téléphone ?"
EMAIL = "Quelle est votre adresse électronique de contact ?"
USED_BY_OWNER = "Exploitez-vous vous-même votre ADS ?"
IS_RENTAL = "Votre ADS est-elle exploitée par un locataire-gérant ?"
RENTAL_SIRET = "Quel est son n° SIRET (14 chiffres)"
EMPLOYEE = "Votre ADS est-elle exploitée par un ou des salarié(es) ?"
NUM_EMPLOYEES = "Combien de salarié(es) exploite(nt) votre ADS"


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "file", type=argparse.FileType("r", encoding="utf8"), help="ADS CSV file"
        )

    def handle(self, file=None, *args, **options):
        epci = EPCI.objects.get(name="CA Pau Béarn Pyrénées")
        ads_manager = ADSManager.objects.get(
            content_type=ContentType.objects.get_for_model(EPCI), object_id=epci.id
        )

        reader = csv.DictReader(file, delimiter=";")
        for row in reader:
            commune = self.load_commune(row[COMMUNE], 64)
            ads_number = f"{commune.libelle} - {row[ADS_NUMBER]}"
            attribution_date = datetime.strptime(row[OWNER_DATE], "%m/%d/%Y")
            assert row[CPAM] in ("Oui", "Non")
            cpam = row[CPAM] == "Oui"

            licence_plate = (
                row[LICENSE_PLATE]
                .strip()
                .replace(".", "")
                .replace(" ", "-")
                .replace("--", "-")
                .upper()
            )

            assert row[ECO_VEHICLE] in ("Oui", "Non")
            eco_vehicle = row[ECO_VEHICLE] == "Oui"

            try:
                siret = validate_siret(row[SIRET])
            except:
                siret = ""
                # print(f"invalid siret: {row[SIRET]}")

            if len(row[PHONE]) != 9:
                phone = ""
            else:
                phone = f"0{row[PHONE]}"

            assert row[USED_BY_OWNER] in ("Oui", "Non")
            used_by_owner = row[USED_BY_OWNER] == "Oui"

            assert row[IS_RENTAL] in ("Oui", "Non", "")
            if row[IS_RENTAL] == "":
                is_rental = None
            else:
                is_rental = row[IS_RENTAL] == "Oui"

            rental_siret = None
            if is_rental:
                try:
                    rental_siret = validate_siret(row[RENTAL_SIRET])
                except:
                    # print(f"invalid rental siret: {row[RENTAL_SIRET]}")
                    pass

            assert row[EMPLOYEE] in ("Oui", "Non", "")
            if row[EMPLOYEE] == "":
                employee = None
            else:
                employee = row[EMPLOYEE] == "Oui"

            if used_by_owner and (is_rental or employee):
                raise ValueError("used_by_owner and is_rental or employee")

            try:
                ads = ADS.objects.get(
                    number=ads_number,
                    ads_manager=ads_manager,
                    epci_commune=commune,
                )
            except ADS.DoesNotExist:
                ads = ADS(
                    number=ads_number,
                    ads_manager=ads_manager,
                )

            ads.ads_creation_date = None
            ads.ads_renew_date = None
            ads.attribution_date = attribution_date
            ads.owner_name = row[OWNER]
            ads.accepted_cpam = cpam
            ads.immatriculation_plate = licence_plate
            ads.eco_vehicle = eco_vehicle
            ads.owner_siret = siret or ""
            ads.owner_phone = phone
            ads.owner_email = row[EMAIL]
            ads.save()

    def load_commune(self, name, departement):
        name = name.strip()
        res = Commune.objects.filter(libelle__iexact=name, departement=departement)
        if len(res.all()) == 1:
            return res[0]
        assert len(res.all()) == 0

        res = Commune.objects.annotate(unaccent_libelle=Unaccent("libelle")).filter(
            unaccent_libelle__iexact=name.replace(" ", "-").strip(),
            departement=departement,
        )
        if len(res.all()) == 1:
            return res[0]

        raise ValueError(f"commune {name} not found")
