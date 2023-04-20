from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from mesads.app.models import ADSManager, ADSManagerAdministrator
from mesads.fradm.models import Commune, EPCI, Prefecture


class Command(BaseCommand):
    help = (
        "Create ADSManager entries for Communes, EPCIs and Prefectures, "
        "create ADSManagerAdministrator entries and grand them permissions to "
        "ADSManager."
    )

    def handle(self, *args, **options):
        with transaction.atomic():
            self.create_ads_managers_for_prefectures()
            self.create_ads_managers_for_epci()
            # self.create_ads_managers_for_communes()
            self.create_administrators()

    def create_ads_managers_for_prefectures(self):
        for prefecture in Prefecture.objects.all():
            ADSManager.objects.get_or_create(
                content_type=ContentType.objects.get_for_model(prefecture),
                object_id=prefecture.id,
            )

    def create_ads_managers_for_epci(self):
        for epci in EPCI.objects.all():
            ADSManager.objects.get_or_create(
                content_type=ContentType.objects.get_for_model(epci), object_id=epci.id
            )

    def create_ads_managers_for_communes(self):
        for commune in Commune.objects.all():
            ADSManager.objects.get_or_create(
                content_type=ContentType.objects.get_for_model(commune),
                object_id=commune.id,
            )

    def create_administrators(self):
        """For each prefecture, create a new ADSManagerAdministrator object and
        add the ressources managed by the prefecture.
        """
        for prefecture in Prefecture.objects.all():
            # Create ADSManagerAdministrator for this Prefecture.
            admin, created = ADSManagerAdministrator.objects.get_or_create(
                prefecture=prefecture
            )

            ADSManager.objects.filter(prefecture__id=prefecture.id).update(
                administrator=admin
            )

            # Prefecture.numero is prefixed with a 0 for numero < 10.
            ADSManager.objects.filter(
                epci__departement=prefecture.numero.lstrip("0")
            ).update(administrator=admin)

            ADSManager.objects.filter(
                commune__departement=prefecture.numero.lstrip("0")
            ).update(administrator=admin)
