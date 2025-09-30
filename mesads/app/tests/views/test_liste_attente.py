import logging
import http
from django.urls import reverse

from mesads.users.unittest import ClientTestCase

from ..factories import (
    ADSManagerRequestFactory,
    ADSManagerFactory,
    InscriptionListeAttenteFactory,
)


class TestADSManagerAdminRequestsView(ClientTestCase):
    def setUp(self):
        super().setUp()
        self.client, self.user = self.create_client()
        self.ads_manager = ADSManagerFactory(for_commune=True)
        self.ads_manager_request = ADSManagerRequestFactory(
            user=self.user, ads_manager=self.ads_manager
        )
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        # Enable logging
        logging.disable(logging.NOTSET)

    def test_get_liste_attente(self):
        inscription = InscriptionListeAttenteFactory(ads_manager=self.ads_manager)
        other_ads_manager = ADSManagerFactory(for_commune=True)
        other_inscription = InscriptionListeAttenteFactory(
            ads_manager=other_ads_manager
        )
        inscription_archived = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager
        )
        inscription_archived.delete()
        inscription_archived.refresh_from_db()

        response = self.client.get(
            reverse("app.liste_attente", kwargs={"manager_id": self.ads_manager.id})
        )
        assert inscription in response.context["inscriptions"]
        assert other_inscription not in response.context["inscriptions"]
        assert inscription_archived not in response.context["inscriptions"]
        self.assertEqual(response.status_code, http.HTTPStatus.OK)
