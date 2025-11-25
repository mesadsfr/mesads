from datetime import datetime, date

from django.core import mail

from mesads.app.models import ADS, ADSManager, ADSManagerRequest
from mesads.unittest import ClientTestCase
from mesads.fradm.models import Prefecture
from mesads.vehicules_relais.models import Vehicule, Proprietaire
from django.urls import reverse
from http import HTTPStatus


class TestADSManagerAdminRequestsView(ClientTestCase):
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
                    f"/espace-prefecture/{self.ads_manager_administrator_35.prefecture_id}/demandes-gestion/"
                )
                self.assertEqual(resp.status_code, expected_status)

    def test_invalid_action(self):
        resp = self.ads_manager_administrator_35_client.post(
            f"/espace-prefecture/{self.ads_manager_administrator_35.prefecture_id}/demandes-gestion/",
            {"action": "xxx", "request_id": 1},
        )
        self.assertEqual(resp.status_code, 400)

    def test_invalid_request_id(self):
        resp = self.ads_manager_administrator_35_client.post(
            f"/espace-prefecture/{self.ads_manager_administrator_35.prefecture_id}/demandes-gestion/",
            {"action": "accept", "request_id": 12342},
        )
        self.assertEqual(resp.status_code, 404)

    def test_accept(self):
        self.assertEqual(len(mail.outbox), 0)

        resp = self.ads_manager_administrator_35_client.post(
            f"/espace-prefecture/{self.ads_manager_administrator_35.prefecture_id}/demandes-gestion/",
            {"action": "accept", "request_id": self.ads_manager_request.id},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            resp.url,
            f"/espace-prefecture/{self.ads_manager_administrator_35.prefecture_id}/demandes-gestion/",
        )
        self.ads_manager_request.refresh_from_db()
        self.assertTrue(self.ads_manager_request.accepted)
        self.assertEqual(len(mail.outbox), 1)

    def test_deny(self):
        self.assertEqual(len(mail.outbox), 0)

        resp = self.ads_manager_administrator_35_client.post(
            f"/espace-prefecture/{self.ads_manager_administrator_35.prefecture_id}/demandes-gestion/",
            {"action": "deny", "request_id": self.ads_manager_request.id},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            resp.url,
            f"/espace-prefecture/{self.ads_manager_administrator_35.prefecture_id}/demandes-gestion/",
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
                f"/espace-prefecture/{self.ads_manager_administrator_35.prefecture_id}/demandes-gestion/",
            )
            self.assertEqual(resp.status_code, 200)

            resp = self.ads_manager_administrator_35_client.get(
                f"/espace-prefecture/{self.ads_manager_administrator_35.prefecture_id}/demandes-gestion/?sort=name",
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
            f"/espace-prefecture/{self.ads_manager_administrator_35.prefecture.id}/changements"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["updates"], [])

        # Create ADS, and update it
        ads = ADS.objects.create(
            number="12346", ads_manager=self.ads_manager_city35, ads_in_use=True
        )
        resp = self.ads_manager_administrator_35_client.post(
            f"/espace-prefecture/{self.ads_manager_administrator_35.prefecture.id}/administrations/{self.ads_manager_city35.id}/ads/{ads.id}",
            {
                "number": ads.id,
                "certify": "true",
                "ads_in_use": "false",
            },
        )
        self.assertEqual(resp.status_code, 302)

        resp = self.ads_manager_administrator_35_client.get(
            f"/espace-prefecture/{self.ads_manager_administrator_35.prefecture.id}/changements"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["updates"]), 1)
        self.assertEqual(len(resp.context["updates"][0]["history_entries"]), 1)

        # # Update the same ADS again
        resp = self.ads_manager_administrator_35_client.post(
            f"/espace-prefecture/{self.ads_manager_administrator_35.prefecture.id}/administrations/{self.ads_manager_city35.id}/ads/{ads.id}",
            {
                "number": ads.id,
                "certify": "true",
                "ads_in_use": "true",
            },
        )
        self.assertEqual(resp.status_code, 302)

        resp = self.ads_manager_administrator_35_client.get(
            f"/espace-prefecture/{self.ads_manager_administrator_35.prefecture.id}/changements"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["updates"]), 1)
        self.assertEqual(len(resp.context["updates"][0]["history_entries"]), 2)


class TestAdsManagerAdministratorView(ClientTestCase):
    def test_get_context(self):
        user_request = ADSManagerRequest.objects.create(
            user=self.ads_manager_administrator_35_user,
            ads_manager=self.ads_manager_city35,
            accepted=True,
        )
        response = self.ads_manager_administrator_35_client.get(
            reverse(
                "app.ads-manager-admin.administrations",
                kwargs={
                    "prefecture_id": self.ads_manager_administrator_35.prefecture.id
                },
            )
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertListEqual(
            [m.id for m in response.context["ads_managers"]],
            list(
                ADSManager.objects.filter(
                    administrator=self.ads_manager_administrator_35
                ).values_list("id", flat=True)
            ),
        )
        self.assertEqual(response.context["user_ads_manager_requests"].count(), 1)
        self.assertEqual(
            response.context["user_ads_manager_requests"].first(), user_request
        )

    def test_post_to_become_gestionnaire(self):
        response = self.ads_manager_administrator_35_client.post(
            reverse(
                "app.ads-manager-admin.administrations",
                kwargs={
                    "prefecture_id": self.ads_manager_administrator_35.prefecture.id
                },
            ),
            data={"ads_manager_id": self.ads_manager_city35.id},
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            ADSManagerRequest.objects.filter(
                user=self.ads_manager_administrator_35_user,
                ads_manager=self.ads_manager_city35,
                accepted=True,
            ).count(),
            1,
        )


class TestRepertoireVehiculeRelaisView(ClientTestCase):
    def setUp(self):
        """Create a proprietaire object, and register vehicules to it."""
        super().setUp()

        self.proprietaire_client, self.proprietaire_user = self.create_client()

        self.proprietaire = Proprietaire.objects.create(nom="Propriétaire")
        self.proprietaire.users.set([self.proprietaire_user])

        prefecture_1 = self.ads_manager_administrator_35.prefecture
        prefecture_2 = Prefecture.objects.filter(numero="33").get()

        # Assign three vehicules to the proprietaire in Ille-et-Vilaine.
        self.vehicule_1 = Vehicule.objects.create(
            proprietaire=self.proprietaire,
            departement=prefecture_1,
            immatriculation="123-456-789",
            modele="Peugeot 308",
            motorisation="essence",
            date_mise_circulation=date(2019, 1, 1),
            nombre_places=4,
            pmr=False,
            commune_localisation=None,
        )
        self.vehicule_2 = Vehicule.objects.create(
            proprietaire=self.proprietaire,
            departement=prefecture_1,
            immatriculation="IMMAT12",
            modele="Peugeot 207",
            motorisation="essence",
            date_mise_circulation=date(2019, 2, 2),
            nombre_places=3,
            pmr=False,
            commune_localisation=None,
        )
        self.vehicule_3 = Vehicule.objects.create(
            proprietaire=self.proprietaire,
            departement=prefecture_2,
            immatriculation="BBBB-BBBB",
            modele="Renault Clio",
            motorisation="hybride",
            date_mise_circulation=date(2023, 5, 1),
            nombre_places=4,
            pmr=False,
            commune_localisation=None,
        )

    def test_get_context(self):
        response = self.ads_manager_administrator_35_client.get(
            reverse(
                "app.ads-manager-admin.vehicules_relais",
                kwargs={
                    "prefecture_id": self.ads_manager_administrator_35.prefecture.id
                },
            )
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.context["ads_manager_administrator"],
            self.ads_manager_administrator_35,
        )
        self.assertEqual(response.context["vehicule_list"].count(), 2)
        self.assertQuerySetEqual(
            response.context["vehicule_list"], [self.vehicule_1, self.vehicule_2]
        )

    def test_get_filtered_context(self):
        response = self.ads_manager_administrator_35_client.get(
            reverse(
                "app.ads-manager-admin.vehicules_relais",
                kwargs={
                    "prefecture_id": self.ads_manager_administrator_35.prefecture.id
                },
            )
            + f"?immatriculation={self.vehicule_1.immatriculation}"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.context["ads_manager_administrator"],
            self.ads_manager_administrator_35,
        )
        self.assertEqual(response.context["vehicule_list"].count(), 1)
        self.assertQuerySetEqual(response.context["vehicule_list"], [self.vehicule_1])


class TestVehiculeView(ClientTestCase):
    def setUp(self):
        """Create a proprietaire object, and register vehicules to it."""
        super().setUp()

        self.proprietaire_client, self.proprietaire_user = self.create_client()

        self.proprietaire = Proprietaire.objects.create(nom="Propriétaire")
        self.proprietaire.users.set([self.proprietaire_user])

        prefecture_1 = self.ads_manager_administrator_35.prefecture

        # Assign three vehicules to the proprietaire in Ille-et-Vilaine.
        self.vehicule = Vehicule.objects.create(
            proprietaire=self.proprietaire,
            departement=prefecture_1,
            immatriculation="123-456-789",
            modele="Peugeot 308",
            motorisation="essence",
            date_mise_circulation=date(2019, 1, 1),
            nombre_places=4,
            pmr=False,
            commune_localisation=None,
        )

    def test_get_context(self):
        response = self.ads_manager_administrator_35_client.get(
            reverse(
                "app.ads-manager-admin.vehicule_relais_detail",
                kwargs={
                    "prefecture_id": self.ads_manager_administrator_35.prefecture.id,
                    "numero": self.vehicule.numero,
                },
            )
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.context["ads_manager_administrator"],
            self.ads_manager_administrator_35,
        )
        self.assertEqual(response.context["vehicule"], self.vehicule)
