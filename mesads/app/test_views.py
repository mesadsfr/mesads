from django.core import mail

from mesads.fradm.models import EPCI, Prefecture

from .models import ADSManagerRequest
from .unittest import ClientTestCase


class TestHomepageView(ClientTestCase):
    def test_redirection(self):
        resp = self.anonymous_client.get('/')
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/auth/login/?next=/')

        resp = self.auth_client.get('/')
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/gestion')

        resp = self.ads_manager_city35_client.get('/')
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/gestion')

        resp = self.ads_manager_administrator_35_client.get('/')
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/admin_gestion')


class TestADSManagerAdminView(ClientTestCase):
    def setUp(self):
        super().setUp()
        self.ads_manager_request = ADSManagerRequest.objects.create(
            user=self.create_user().obj,
            ads_manager=self.ads_manager_city35,
            accepted=None
        )

    def test_invalid_action(self):
        resp = self.ads_manager_administrator_35_client.post(
            '/admin_gestion',
            {'action': 'xxx', 'request_id': 1}
        )
        self.assertEqual(resp.status_code, 400)

    def test_invalid_request_id(self):
        resp = self.ads_manager_administrator_35_client.post(
            '/admin_gestion',
            {'action': 'accept', 'request_id': 12342}
        )
        self.assertEqual(resp.status_code, 404)

    def test_accept(self):
        self.assertEqual(len(mail.outbox), 0)

        resp = self.ads_manager_administrator_35_client.post(
            '/admin_gestion',
            {'action': 'accept', 'request_id': self.ads_manager_request.id}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/admin_gestion')
        self.ads_manager_request.refresh_from_db()
        self.assertTrue(self.ads_manager_request.accepted)
        self.assertEqual(len(mail.outbox), 1)

    def test_deny(self):
        self.assertEqual(len(mail.outbox), 0)

        resp = self.ads_manager_administrator_35_client.post(
            '/admin_gestion',
            {'action': 'deny', 'request_id': self.ads_manager_request.id}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/admin_gestion')
        self.ads_manager_request.refresh_from_db()
        self.assertFalse(self.ads_manager_request.accepted)
        self.assertEqual(len(mail.outbox), 1)


class TestADSManagerRequestView(ClientTestCase):
    def setUp(self):
        super().setUp()
        self.initial_ads_managers_count = ADSManagerRequest.objects.count()

    def test_create_request_invalid_id(self):
        """Provide the id of a non-existing object."""
        resp = self.auth_client.post('/gestion', {
            'commune': 9999
        })
        self.assertIn('error', resp.content.decode('utf8'))

    def test_create_request_commune(self):
        resp = self.auth_client.post('/gestion', {
            'commune': self.commune_melesse.id
        })
        self.assertNotIn('error', resp.content.decode('utf8'))
        self.assertEqual(ADSManagerRequest.objects.count(), self.initial_ads_managers_count + 1)

        # Make sure django message is in the next request
        resp = self.auth_client.get('/gestion')
        self.assertEqual(len(resp.context['messages']), 1)

        # If there is a ADSManagerAdministrator related to the commune, an email is sent for each member.
        # The base class ClientTestCase configures Melesse to be managed by the ADSManagerAdministrator entry of
        # l'Ille-et-Vilaine.
        self.assertEqual(len(mail.outbox), 1)

    def test_create_request_epci(self):
        epci = EPCI.objects.first()
        resp = self.auth_client.post('/gestion', {
            'epci': epci.id
        })
        self.assertNotIn('error', resp.content.decode('utf8'))
        self.assertEqual(ADSManagerRequest.objects.count(), self.initial_ads_managers_count + 1)

        # Make sure django message is in the next request
        resp = self.auth_client.get('/gestion')
        self.assertEqual(len(resp.context['messages']), 1)

    def test_create_request_prefecture(self):
        prefecture = Prefecture.objects.first()
        resp = self.auth_client.post('/gestion', {
            'prefecture': prefecture.id
        })
        self.assertNotIn('error', resp.content.decode('utf8'))
        self.assertEqual(ADSManagerRequest.objects.count(), self.initial_ads_managers_count + 1)

        # Make sure django message is in the next request
        resp = self.auth_client.get('/gestion')
        self.assertEqual(len(resp.context['messages']), 1)
