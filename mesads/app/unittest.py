import logging

from django.contrib.contenttypes.models import ContentType

from mesads.fradm.models import Commune, Prefecture
from mesads.fradm.unittest import ClientTestCase as BaseClientTestCase

from .models import ADSManager, ADSManagerAdministrator, ADSManagerRequest


class ClientTestCase(BaseClientTestCase):
    def setUp(self):
        """Create the following attributes:

        * ads_manager_city35_client: ADSManager of the city of Melesse (which belongs to the
                                     prefecture 35 - Ille-et-Vilaine)
        * ads_manager_administrator_35_client = ADSManagerAdministrator of the Prefecture of 35 - Ille-et-Vilaine
        """
        super().setUp()

        # Create User and authenticate flask client
        self.ads_manager_city35_client, ads_manager_city35_user = self.create_client()

        # Retrieve ADSManager entry for Melesse created in self.create_fixtures()
        self.commune_melesse = Commune.objects.filter(libelle="Melesse").get()
        self.ads_manager_city35 = ADSManager.objects.get(
            content_type=ContentType.objects.get_for_model(self.commune_melesse),
            object_id=self.commune_melesse.id,
        )

        # Give permissions to client by creating an entry in ADSManagerRequest
        self.ads_manager_request = ADSManagerRequest.objects.create(
            user=ads_manager_city35_user,
            ads_manager=self.ads_manager_city35,
            accepted=True,
        )

        # Create User and authenticate flask client
        (
            self.ads_manager_administrator_35_client,
            self.ads_manager_administrator_35_user,
        ) = self.create_client()

        prefecture = Prefecture.objects.filter(numero=35).get()
        self.ads_manager_administrator_35 = ADSManagerAdministrator.objects.get(
            prefecture=prefecture
        )
        self.ads_manager_administrator_35.users.add(
            self.ads_manager_administrator_35_user
        )

        # Disable logging below critical to avoid useless messages during
        # unittests (requests error 404 for example).
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        # Enable logging
        logging.disable(logging.NOTSET)

    def create_fixtures(self):
        """Create ADSManager and ADSManagerAdministrator entries.

        This code simulates the custom command "load_ads_managers".
        """
        super().create_fixtures()

        # For each prefecture, create a ADSManager entry and a ADSManagerAdministrator entry.
        # Also, for each commune of the prefecture, configures
        for prefecture in self.fixtures_prefectures:
            ads_manager_administrator = ADSManagerAdministrator.objects.create(
                prefecture=prefecture
            )
            ads_manager = ADSManager.objects.create(
                content_object=prefecture, administrator=ads_manager_administrator
            )
            ads_manager.save()

        # Create a ADSManager entry for each commune
        for commune in self.fixtures_communes:
            administrator = ADSManagerAdministrator.objects.filter(
                prefecture__numero=commune.departement
            ).get()
            ADSManager.objects.create(
                content_object=commune, administrator=administrator
            )

        # Create a ADSManager entry for each EPCI
        for epci in self.fixtures_epci:
            administrator = ADSManagerAdministrator.objects.filter(
                prefecture__numero=epci.departement
            ).get()
            ADSManager.objects.create(content_object=epci, administrator=administrator)
