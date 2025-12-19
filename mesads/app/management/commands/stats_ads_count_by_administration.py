import csv
import sys

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from mesads.app.models import ADSManager
from mesads.fradm.models import EPCI, Commune, Prefecture


class Command(BaseCommand):
    help = "Generate stats about ADS count by administration"

    def handle(self, *args, **kwargs):
        ct_commune = ContentType.objects.get_for_model(Commune)
        ct_epci = ContentType.objects.get_for_model(EPCI)
        ct_prefecture = ContentType.objects.get_for_model(Prefecture)

        departements = {
            prefecture.numero: prefecture.libelle
            for prefecture in Prefecture.objects.all()
        }

        writer = csv.writer(sys.stdout)

        writer.writerow(
            [
                "Département",
                "Nom département",
                "Type de l'administration",
                "Nom de l'administration",
                "Code INSEE",
                "Nombre d'ADS",
            ]
        )

        for ads_manager in ADSManager.objects.all():
            departement_numero = ""
            insee = ""

            if ads_manager.content_type == ct_commune:
                departement_numero = ads_manager.content_object.departement
                insee = ads_manager.content_object.insee
            elif ads_manager.content_type == ct_epci:
                departement_numero = ads_manager.content_object.departement
            elif ads_manager.content_type == ct_prefecture:
                departement_numero = ads_manager.content_object.numero

            writer.writerow(
                [
                    departement_numero,
                    departements[departement_numero],
                    ads_manager.content_object.type_name(),
                    ads_manager.content_object.text(),
                    insee,
                    ads_manager.ads_set.count(),
                ]
            )
