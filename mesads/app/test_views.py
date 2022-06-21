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
