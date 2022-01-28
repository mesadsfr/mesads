from django.core.management.base import BaseCommand
from django.db import transaction

from mesads.app.models import ADSManager, ADSManagerAdministrator
from mesads.fradm.models import Commune, EPCI, Prefecture


class Command(BaseCommand):
    help = ('Create ADSManager entries for Communes, EPCIs and Prefectures, '
            'create ADSManagerAdministrator entries and grand them permissions to '
            'ADSManager.')

    def handle(self, *args, **options):
        with transaction.atomic():
            self.create_ads_managers_for_prefectures()
            self.create_ads_managers_for_epci()
            self.create_ads_managers_for_communes()
            self.create_administrators()

    def create_ads_managers_for_prefectures(self):
        for prefecture in Prefecture.objects.all():
            obj = ADSManager(content_object=prefecture)
            obj.save()

    def create_ads_managers_for_epci(self):
        for epci in EPCI.objects.all():
            obj = ADSManager(content_object=epci)
            obj.save()

    def create_ads_managers_for_communes(self):
        for commune in Commune.objects.all():
            obj = ADSManager(content_object=commune)
            obj.save()

    def create_administrators(self):
        """For each prefecture, create a new ADSManagerAdministrator object and
        add the ressources managed by the prefecture.
        """
        for prefecture in Prefecture.objects.all():
            # Create ADSManagerAdministrator for this Prefecture.
            admin, created = ADSManagerAdministrator.objects.get_or_create(prefecture=prefecture)

            # Add ADSManager entry related to the Prefecture
            admin.ads_managers.add(
                ADSManager.objects.filter(prefecture__id=prefecture.id).get()
            )

            # Add ADSManager entries for EPCI with the matching departement.
            for epci_mgr in ADSManager.objects.filter(
                epci__departement=prefecture.numero
            ):
                admin.ads_managers.add(epci_mgr)

            # Add ADSManager entries for Communes with the maching departement.
            for commune_mgr in ADSManager.objects.filter(
                commune__departement=prefecture.numero
            ):
                admin.ads_managers.add(commune_mgr)
