import csv
import sys

from django.core.management.base import BaseCommand
from django.db.models import Count

from mesads.app.models import ADSManager
from mesads.fradm.models import EPCI, Commune, Prefecture


class Command(BaseCommand):
    help = "Export a CSV file with the count of ADS for each ADSm anager."

    def handle(self, *args, **options):
        writer = csv.DictWriter(
            sys.stdout,
            fieldnames=[
                "Département",
                "Nom département",
                "Type d'administration",
                "Nom de l'administration",
                "Code INSEE",
                "Nombre d'ADS",
            ],
        )

        writer.writeheader()

        query = ADSManager.objects.annotate(ads_count=Count("ads")).filter(
            ads_count__gt=0
        )

        prefectures = {
            prefecture.numero: prefecture.libelle
            for prefecture in Prefecture.objects.all()
        }

        for row in query:
            prefecture = None
            insee = None

            if issubclass(row.content_type.model_class(), Commune):
                if row.content_object.libelle == "Test MesADS":
                    continue
                prefecture = row.content_object.departement
                insee = row.content_object.insee
            elif issubclass(row.content_type.model_class(), EPCI):
                if row.content_object.name == "CC Test MesADS":
                    continue
                prefecture = row.content_object.departement
            elif issubclass(row.content_type.model_class(), Prefecture):
                if row.content_object.libelle == "Test-MesADS":
                    continue
                prefecture = row.content_object.numero

            writer.writerow(
                {
                    "Département": prefecture,
                    "Nom département": prefectures[prefecture],
                    "Type d'administration": row.content_object.type_name(),
                    "Nom de l'administration": row.content_object.text(),
                    "Code INSEE": insee,
                    "Nombre d'ADS": row.ads_count,
                }
            )
