import collections

from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType


from mesads.app.models import ADS
from mesads.fradm.models import Commune, EPCI, Prefecture


class Command(BaseCommand):
    help = "Generate stats about ADS count by PMR by department"

    def handle(self, *args, **kwargs):
        stats = collections.defaultdict(
            lambda: collections.defaultdict(lambda: collections.defaultdict(int))
        )

        query = (
            ADS.objects.prefetch_related("ads_manager__content_type")
            .prefetch_related("ads_manager__content_object")
            .all()
        )

        ct_commune = ContentType.objects.get_for_model(Commune)
        ct_epci = ContentType.objects.get_for_model(EPCI)
        ct_prefecture = ContentType.objects.get_for_model(Prefecture)

        for ads in query:
            if ads.ads_manager.content_type == ct_commune:
                entry = stats[ads.ads_manager.content_object.departement]["Communes"]
            elif ads.ads_manager.content_type == ct_epci:
                entry = stats[ads.ads_manager.content_object.departement]["EPCI"]
            elif ads.ads_manager.content_type == ct_prefecture:
                entry = stats[ads.ads_manager.content_object.numero]["Préfecture"]

            entry[ads.vehicle_compatible_pmr] += 1

        for departement, data in sorted(stats.items()):
            print(f"Department {departement}")
            for type_, values in sorted(data.items()):
                print(f"  {type_}")
                for pmr, count in values.items():
                    if pmr is None:
                        pmr = "Statut inconnu"
                    elif pmr:
                        pmr = "Véhicules compatibles PMR"
                    else:
                        pmr = "Véhicules non compatibles PMR"
                    print(f"    {pmr}: {count}")
