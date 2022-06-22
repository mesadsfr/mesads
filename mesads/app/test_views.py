from django.core import mail

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
