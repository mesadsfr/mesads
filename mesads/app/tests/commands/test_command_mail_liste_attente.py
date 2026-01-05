import datetime
import logging

from django.conf import settings
from django.core import mail
from django.core.management import call_command
from django.urls import reverse

from mesads.app.models import InscriptionListeAttente
from mesads.users.unittest import ClientTestCase as BaseClientTestCase

from ..factories import (
    ADSManagerFactory,
    ADSManagerRequestFactory,
    InscriptionListeAttenteFactory,
)


class ClientTestCase(BaseClientTestCase):
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


class TestListeAttenteView(ClientTestCase):
    def test_get_liste_attente(self):
        date_contact = datetime.date.today() - datetime.timedelta(days=5)

        inscription_1 = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager,
            status=InscriptionListeAttente.ATTENTE_REPONSE,
            date_contact=date_contact,
            delai_reponse=4,
        )

        inscription_2 = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager,
            status=InscriptionListeAttente.ATTENTE_REPONSE,
            date_contact=date_contact,
            delai_reponse=4,
        )

        inscription_3 = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager,
            status=InscriptionListeAttente.ATTENTE_REPONSE,
            date_contact=date_contact,
            delai_reponse=5,
        )

        inscription_4 = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager,
            status=InscriptionListeAttente.ATTENTE_REPONSE,
            date_contact=date_contact,
            delai_reponse=3,
        )

        call_command("liste_attente_mail_delai_depasse")
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, [self.user.email])
        self.assertIn(settings.MESADS_BASE_URL, email.body)
        self.assertIn(
            reverse(
                "app.liste_attente_traitement_demande",
                kwargs={
                    "manager_id": self.ads_manager.id,
                    "inscription_id": inscription_1.id,
                },
            ),
            email.body,
        )
        self.assertIn(
            reverse(
                "app.liste_attente_traitement_demande",
                kwargs={
                    "manager_id": self.ads_manager.id,
                    "inscription_id": inscription_2.id,
                },
            ),
            email.body,
        )
        self.assertNotIn(
            reverse(
                "app.liste_attente_traitement_demande",
                kwargs={
                    "manager_id": self.ads_manager.id,
                    "inscription_id": inscription_3.id,
                },
            ),
            email.body,
        )
        self.assertNotIn(
            reverse(
                "app.liste_attente_traitement_demande",
                kwargs={
                    "manager_id": self.ads_manager.id,
                    "inscription_id": inscription_4.id,
                },
            ),
            email.body,
        )
