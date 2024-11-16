from datetime import datetime

from django.core import mail

from ..models import ADS, ADSManager, ADSManagerRequest
from ..unittest import ClientTestCase


class ADSManagerAdminIndexView(ClientTestCase):
    def test_redirect(self):
        resp = self.ads_manager_administrator_35_client.get(
            "/registre_ads/admin_gestion"
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            resp.url,
            f"/registre_ads/admin_gestion/{self.ads_manager_administrator_35.prefecture_id}",
        )

        client, _ = self.create_client(admin=True)

        # Admin, but not ADSManagerAdministrator
        resp = client.get("/registre_ads/admin_gestion")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            resp.url,
            "/registre_ads/gestion",
        )


class TestADSManagerAdminView(ClientTestCase):
    def setUp(self):
        super().setUp()
        self.ads_manager_request = ADSManagerRequest.objects.create(
            user=self.create_user().obj,
            ads_manager=self.ads_manager_city35,
            accepted=None,
        )

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
                    f"/registre_ads/admin_gestion/{self.ads_manager_administrator_35.prefecture_id}"
                )
                self.assertEqual(resp.status_code, expected_status)

    def test_invalid_action(self):
        resp = self.ads_manager_administrator_35_client.post(
            f"/registre_ads/admin_gestion/{self.ads_manager_administrator_35.prefecture_id}",
            {"action": "xxx", "request_id": 1},
        )
        self.assertEqual(resp.status_code, 400)

    def test_invalid_request_id(self):
        resp = self.ads_manager_administrator_35_client.post(
            f"/registre_ads/admin_gestion/{self.ads_manager_administrator_35.prefecture_id}",
            {"action": "accept", "request_id": 12342},
        )
        self.assertEqual(resp.status_code, 404)

    def test_accept(self):
        self.assertEqual(len(mail.outbox), 0)

        resp = self.ads_manager_administrator_35_client.post(
            f"/registre_ads/admin_gestion/{self.ads_manager_administrator_35.prefecture_id}",
            {"action": "accept", "request_id": self.ads_manager_request.id},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            resp.url,
            f"/registre_ads/admin_gestion/{self.ads_manager_administrator_35.prefecture_id}",
        )
        self.ads_manager_request.refresh_from_db()
        self.assertTrue(self.ads_manager_request.accepted)
        self.assertEqual(len(mail.outbox), 1)

    def test_deny(self):
        self.assertEqual(len(mail.outbox), 0)

        resp = self.ads_manager_administrator_35_client.post(
            f"/registre_ads/admin_gestion/{self.ads_manager_administrator_35.prefecture_id}",
            {"action": "deny", "request_id": self.ads_manager_request.id},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            resp.url,
            f"/registre_ads/admin_gestion/{self.ads_manager_administrator_35.prefecture_id}",
        )
        self.ads_manager_request.refresh_from_db()
        self.assertFalse(self.ads_manager_request.accepted)
        self.assertEqual(len(mail.outbox), 1)

    def test_sort(self):
        for ads_manager in ADSManager.objects.all():
            ADSManagerRequest.objects.create(
                user=self.create_user().obj,
                ads_manager=ads_manager,
                accepted=None,
            )
            resp = self.ads_manager_administrator_35_client.get(
                f"/registre_ads/admin_gestion/{self.ads_manager_administrator_35.prefecture_id}",
            )
            self.assertEqual(resp.status_code, 200)

            resp = self.ads_manager_administrator_35_client.get(
                f"/registre_ads/admin_gestion/{self.ads_manager_administrator_35.prefecture_id}?sort=name",
            )
            self.assertEqual(resp.status_code, 200)


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


class TestADSManagerAdminUpdatesView(ClientTestCase):
    def test_updates(self):
        resp = self.ads_manager_administrator_35_client.get(
            f"/registre_ads/admin_gestion/{self.ads_manager_administrator_35.prefecture.id}/changements"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["updates"], [])

        # Create ADS, and update it
        ads = ADS.objects.create(
            number="12346", ads_manager=self.ads_manager_city35, ads_in_use=True
        )
        resp = self.ads_manager_administrator_35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{ads.id}",
            {
                "number": ads.id,
                "ads_in_use": "false",
            },
        )
        self.assertEqual(resp.status_code, 302)

        resp = self.ads_manager_administrator_35_client.get(
            f"/registre_ads/admin_gestion/{self.ads_manager_administrator_35.prefecture.id}/changements"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["updates"]), 1)
        self.assertEqual(len(resp.context["updates"][0]["history_entries"]), 1)

        # # Update the same ADS again
        resp = self.ads_manager_administrator_35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{ads.id}",
            {
                "number": ads.id,
                "ads_in_use": "true",
            },
        )
        self.assertEqual(resp.status_code, 302)

        resp = self.ads_manager_administrator_35_client.get(
            f"/registre_ads/admin_gestion/{self.ads_manager_administrator_35.prefecture.id}/changements"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["updates"]), 1)
        self.assertEqual(len(resp.context["updates"][0]["history_entries"]), 2)
