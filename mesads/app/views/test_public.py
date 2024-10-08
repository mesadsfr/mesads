from datetime import datetime

from django.test import RequestFactory

from mesads.app.models import ADS
from mesads.app.views import HTTP500View

from ..unittest import ClientTestCase


class TestHTTP500View(ClientTestCase):
    def test_500(self):
        request = RequestFactory().get("/500")
        response = HTTP500View.as_view()(request)
        self.assertEqual(response.status_code, 200)

        # POST requests should be allowed
        request = RequestFactory().post("/500")
        response = HTTP500View.as_view()(request)
        self.assertEqual(response.status_code, 200)


class TestHomepageView(ClientTestCase):
    def test_200(self):
        resp = self.anonymous_client.get("/")
        self.assertEqual(resp.status_code, 200)


class TestProfileADSManagerAdministratorView(ClientTestCase):
    def test_200(self):
        resp = self.anonymous_client.get("/prefecture")
        self.assertEqual(resp.status_code, 200)


class TestProfileADSManagerView(ClientTestCase):
    def test_200(self):
        resp = self.anonymous_client.get("/gestionnaire_ads")
        self.assertEqual(resp.status_code, 200)


class TestProfileDriverView(ClientTestCase):
    def test_200(self):
        resp = self.anonymous_client.get("/chauffeur")
        self.assertEqual(resp.status_code, 200)


class TestADSRegisterView(ClientTestCase):
    def test_redirection(self):
        for client_name, client, expected_status, redirect_url in (
            (
                "anonymous",
                self.anonymous_client,
                302,
                "/auth/login/?next=/registre_ads/",
            ),
            ("auth", self.auth_client, 302, "/registre_ads/gestion"),
            (
                "ads_manager 35",
                self.ads_manager_city35_client,
                302,
                "/registre_ads/gestion",
            ),
            (
                "ads_manager_admin 35",
                self.ads_manager_administrator_35_client,
                302,
                "/registre_ads/admin_gestion",
            ),
            ("admin", self.admin_client, 302, "/registre_ads/dashboards"),
        ):
            with self.subTest(
                client_name=client_name,
                expected_status=expected_status,
                redirect_url=redirect_url,
            ):
                resp = client.get("/registre_ads/")
                self.assertEqual(resp.status_code, expected_status)
                self.assertEqual(resp.url, redirect_url)


class TestFAQView(ClientTestCase):
    def test_get(self):
        resp = self.client.get("/faq")
        self.assertEqual(resp.status_code, 200)


class TestStatsView(ClientTestCase):
    def test_get(self):
        resp = self.anonymous_client.get("/chiffres-cles")
        self.assertEqual(resp.status_code, 200)

    def test_get_filter(self):
        ADS.objects.create(
            number="1",
            ads_manager=self.ads_manager_city35,
            ads_creation_date=datetime.now().date(),
            ads_in_use=True,
        )

        resp = self.anonymous_client.get("/chiffres-cles?q=xxx")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["ads_count"], 1)
        self.assertEqual(resp.context["ads_count_filtered"], 0)

        resp = self.anonymous_client.get(
            f"/chiffres-cles?q={self.ads_manager_city35.id}"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["ads_count"], 1)
        self.assertEqual(resp.context["ads_count_filtered"], 1)

        # Invalid filter, unexisting id
        resp = self.anonymous_client.get("/chiffres-cles?q=9999999")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["ads_count"], 1)
        self.assertEqual(resp.context["ads_count_filtered"], 0)


class TestReglementationView(ClientTestCase):
    def test_get(self):
        resp = self.anonymous_client.get("/reglementation")
        self.assertEqual(resp.status_code, 200)
