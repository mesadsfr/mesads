from django.test import RequestFactory
from django.urls import reverse

from mesads.app.models import ADSManagerRequest
from mesads.app.views import HTTP500View
from mesads.vehicules_relais.models import Proprietaire
from mesads.unittest import ClientTestCase


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
        response = self.anonymous_client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context.get("administrateur_ads"))
        self.assertIsNone(response.context.get("ads_manager_administrator"))
        self.assertIsNone(response.context.get("manager_ads"))
        self.assertIsNone(response.context.get("requetes_gestionnaires"))
        self.assertIsNone(response.context.get("proprietaire_vehicule_relais"))

    def test_get_as_authenticated_user(self):
        client_connecte, _ = self.create_client()
        response = client_connecte.get("/")

        self.assertEqual(response.status_code, 200)

        self.assertIsNone(response.context.get("administrateur_ads"))
        self.assertIsNone(response.context.get("ads_manager_administrator"))
        self.assertIsNone(response.context.get("manager_ads"))
        self.assertIsNone(response.context.get("requetes_gestionnaires"))
        self.assertIsNone(response.context.get("proprietaire_vehicule_relais"))

    def test_get_as_ads_manager(self):
        response = self.ads_manager_city35_client.get("/")

        self.assertEqual(response.status_code, 200)

        self.assertIsNone(response.context.get("administrateur_ads"))
        self.assertIsNone(response.context.get("ads_manager_administrator"))

        self.assertTrue(response.context.get("manager_ads"))
        self.assertQuerySetEqual(
            response.context.get("requetes_gestionnaires"),
            ADSManagerRequest.objects.filter(user=self.ads_manager_city35_user),
        )

        self.assertIsNone(response.context.get("proprietaire_vehicule_relais"))

    def test_get_as_administrator(self):
        response = self.ads_manager_administrator_35_client.get("/")

        self.assertEqual(response.status_code, 200)

        self.assertTrue(response.context.get("administrateur_ads"))
        self.assertEqual(
            response.context.get("ads_manager_administrator"),
            self.ads_manager_administrator_35,
        )

        self.assertIsNone(response.context.get("manager_ads"))
        self.assertIsNone(response.context.get("requetes_gestionnaires"))
        self.assertIsNone(response.context.get("proprietaire_vehicule_relais"))

    def test_get_as_proprietaire(self):
        client_proprietaire, user_proprietaire = self.create_client()

        proprietaire = Proprietaire.objects.create(nom="Propriétaire")
        proprietaire.users.set([user_proprietaire])

        response = client_proprietaire.get("/")

        self.assertEqual(response.status_code, 200)

        self.assertIsNone(response.context.get("administrateur_ads"))
        self.assertIsNone(response.context.get("ads_manager_administrator"))
        self.assertIsNone(response.context.get("manager_ads"))
        self.assertIsNone(response.context.get("requetes_gestionnaires"))
        self.assertTrue(response.context.get("proprietaire_vehicule_relais"))


class TestFAQView(ClientTestCase):
    def test_get(self):
        resp = self.client.get("/faq")
        self.assertEqual(resp.status_code, 200)


class TestStatsView(ClientTestCase):
    def test_get(self):
        resp = self.anonymous_client.get("/chiffres-cles")
        self.assertEqual(resp.status_code, 200)


class TestReglementationView(ClientTestCase):
    def test_get(self):
        resp = self.anonymous_client.get("/reglementation")
        self.assertEqual(resp.status_code, 200)


class TestPlanSiteView(ClientTestCase):
    def test_200(self):
        response = self.anonymous_client.get(reverse("app.plan_site"))
        self.assertEqual(response.status_code, 200)

    def test_get_as_authenticated_user(self):
        client_connecte, _ = self.create_client()
        response = client_connecte.get(reverse("app.plan_site"))
        self.assertEqual(response.status_code, 200)

    def test_get_as_ads_manager(self):
        response = self.ads_manager_city35_client.get(reverse("app.plan_site"))

        self.assertEqual(response.status_code, 200)

    def test_get_as_administrator(self):
        response = self.ads_manager_administrator_35_client.get(
            reverse("app.plan_site")
        )

        self.assertEqual(response.status_code, 200)

    def test_get_as_proprietaire(self):
        client_proprietaire, user_proprietaire = self.create_client()

        proprietaire = Proprietaire.objects.create(nom="Propriétaire")
        proprietaire.users.set([user_proprietaire])

        response = client_proprietaire.get(reverse("app.plan_site"))

        self.assertEqual(response.status_code, 200)
