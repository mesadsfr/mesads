from mesads.unittest import ClientTestCase


class TestDashboardsViews(ClientTestCase):
    """Test DashboardsView and DashboardsDetailView"""

    def test_permissions(self):
        for client_name, client, expected_status in (
            ("anonymous", self.anonymous_client, 302),
            ("auth", self.auth_client, 302),
            ("ads_manager 35", self.ads_manager_city35_client, 302),
            ("ads_manager_admin 35", self.ads_manager_administrator_35_client, 302),
            ("admin", self.admin_client, 200),
        ):
            with self.subTest(client_name=client_name, expected_status=expected_status):
                resp = client.get("/registre_ads/dashboards")
                self.assertEqual(resp.status_code, expected_status)

    def test_get(self):
        resp = self.admin_client.get("/registre_ads/dashboards")
        self.assertEqual(resp.status_code, 200)
