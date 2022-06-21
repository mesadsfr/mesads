from django.contrib.contenttypes.models import ContentType

from mesads.fradm.models import Commune, Prefecture
from mesads.fradm.unittest import ClientTestCase as BaseClientTestCase

from .models import ADSManager, ADSManagerAdministrator, ADSManagerRequest


class ClientTestCase(BaseClientTestCase):
    def setUp(self):
        """Create the following attributes:

        * ads_manager_city35_client: ADSManager of the city of Melesse (which belongs to the
                                     prefecture 35 - Ille-et-Vilaine)
        * asd_manager_administrator_pref35_client = ADSManagerAdministrator of the Prefecture of 35 - Ille-et-Vilaine
        """
        super().setUp()

        # Create User and authenticate flask client
        self.ads_manager_city35_client, ads_manager_city35_user = self.create_client()

        # Retrieve ADSManager entry for Melesse created in self.create_fixtures()
        commune_melesse = Commune.objects.filter(libelle='Melesse').get()
        ads_manager_city35 = ADSManager.objects.get(
            content_type=ContentType.objects.get_for_model(commune_melesse),
            object_id=commune_melesse.id
        )

        # Give permissions to client by creating an entry in ADSManagerRequest
        ADSManagerRequest.objects.create(
            user=ads_manager_city35_user,
            ads_manager=ads_manager_city35,
            accepted=True
        )

        # Create User and authenticate flask client
        self.ads_manager_administrator_35_client, ads_manager_administrator_35_user = self.create_client()

        prefecture = Prefecture.objects.filter(numero=35).get()
        ads_manager_administrator_35 = ADSManagerAdministrator.objects.get(prefecture=prefecture)
        ads_manager_administrator_35.users.add(ads_manager_administrator_35_user)

    def create_fixtures(self):
        """Create ADSManager and ADSManagerAdministrator entries.
        """
        super().create_fixtures()

        for commune in self.fixtures_communes:
            ADSManager.objects.create(content_object=commune)

        for epci in self.fixtures_epci:
            ADSManager.objects.create(content_object=epci)

        for prefecture in self.fixtures_prefectures:
            ads_manager = ADSManager.objects.create(content_object=prefecture)
            ads_manager_administrator = ADSManagerAdministrator.objects.create(prefecture=prefecture)

            for commune in self.fixtures_communes:
                if commune.departement == prefecture.numero:
                    ads_manager_administrator.ads_managers.add(ads_manager)
