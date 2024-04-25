from datetime import datetime

from ..models import (
    ADS,
)
from ..unittest import ClientTestCase


class TestExportPrefecture(ClientTestCase):
    def test_permissions(self):
        for client_name, client, expected_status in (
            ("admin", self.admin_client, 200),
            ("anonymous", self.anonymous_client, 302),
            ("auth", self.auth_client, 404),
            ("ads_manager 35", self.ads_manager_city35_client, 404),
            ("ads_manager_admin 35", self.ads_manager_administrator_35_client, 200),
        ):
            with self.subTest(client_name=client_name, expected_status=expected_status):
                resp = client.get(
                    f"/registre_ads/prefectures/{self.ads_manager_administrator_35.prefecture.id}/export"
                )
                self.assertEqual(resp.status_code, expected_status)

    def test_get_404(self):
        resp = self.ads_manager_administrator_35_client.get(
            "/registre_ads/prefectures/9999/export"
        )
        self.assertEqual(resp.status_code, 404)

    def test_export(self):
        ADS.objects.create(
            number="1",
            ads_manager=self.ads_manager_city35,
            accepted_cpam=True,
            ads_in_use=True,
        )
        ADS.objects.create(
            number="2",
            ads_manager=self.ads_manager_city35,
            ads_in_use=True,
        )
        ADS.objects.create(
            number="3",
            ads_manager=self.ads_manager_city35,
            ads_creation_date=datetime.now().date(),
            ads_in_use=True,
        )

        resp = self.ads_manager_administrator_35_client.get(
            f"/registre_ads/prefectures/{self.ads_manager_administrator_35.prefecture.id}/export"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.headers["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def test_export_no_ads_declared(self):
        """Similar to test_export, but with no_ads_declared for the ADSManager."""
        self.ads_manager_city35.no_ads_declared = True
        self.ads_manager_city35.save()

        ADS.objects.create(
            number="1",
            ads_manager=self.ads_manager_city35,
            accepted_cpam=True,
            ads_in_use=True,
        )
        resp = self.ads_manager_administrator_35_client.get(
            f"/registre_ads/prefectures/{self.ads_manager_administrator_35.prefecture.id}/export"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.headers["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def test_export_epci_delegate(self):
        """Similar to test_export, but with epci_delegate for the ADSManager."""
        self.ads_manager_city35.epci_delegate = self.fixtures_epci[0]
        self.ads_manager_city35.save()

        ADS.objects.create(
            number="1",
            ads_manager=self.ads_manager_city35,
            accepted_cpam=True,
            ads_in_use=True,
        )
        resp = self.ads_manager_administrator_35_client.get(
            f"/registre_ads/prefectures/{self.ads_manager_administrator_35.prefecture.id}/export"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.headers["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
