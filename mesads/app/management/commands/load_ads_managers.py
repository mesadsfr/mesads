from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from mesads.app.models import ADSManager, ADSManagerAdministrator
from mesads.fradm.models import Commune, EPCI, Prefecture


class Command(BaseCommand):
    help = (
        "Create ADSManager entries for Communes, EPCIs and Prefectures, "
        "create ADSManagerAdministrator entries and grant them permissions to "
        "ADSManager."
    )

    def handle(self, *args, **options):
        with transaction.atomic():
            prefectures = self.create_administrators()
            self.create_ads_managers_for_prefectures(prefectures)
            self.create_ads_managers_for_epci(prefectures)
            self.create_ads_managers_for_communes(prefectures)

    def create_ads_managers_for_prefectures(self, prefectures):
        for prefecture in Prefecture.objects.all():
            ADSManager.objects.get_or_create(
                content_type=ContentType.objects.get_for_model(prefecture),
                object_id=prefecture.id,
                administrator=prefectures[prefecture.numero],
            )

    def create_ads_managers_for_epci(self, prefectures):
        for epci in EPCI.objects.all():
            ADSManager.objects.get_or_create(
                content_type=ContentType.objects.get_for_model(epci),
                object_id=epci.id,
                administrator=prefectures[epci.departement],
            )

    def create_ads_managers_for_communes(self, prefectures):
        for commune in Commune.objects.all():
            ADSManager.objects.get_or_create(
                content_type=ContentType.objects.get_for_model(commune),
                object_id=commune.id,
                administrator=prefectures[commune.departement],
            )

    def create_administrators(self):
        """For each prefecture, create a new ADSManagerAdministrator object and
        add the ressources managed by the prefecture.
        """
        prefectures = {}
        for prefecture in Prefecture.objects.all():
            # Create ADSManagerAdministrator for this Prefecture.
            admin, created = ADSManagerAdministrator.objects.get_or_create(
                prefecture=prefecture
            )
            prefectures[prefecture.numero] = admin
        return prefectures
