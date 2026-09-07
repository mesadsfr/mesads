import datetime

from django.urls import reverse

from mesads.app.models import DemandeAccesLectureSeule, DemandeGestionPrefecture
from mesads.app.tests.factories import (
    ADSManagerAdministratorFactory,
    ADSManagerFactory,
    ADSManagerRequestFactory,
    CommuneFactory,
)
from mesads.users.unittest import ClientTestCase as CTC
from mesads.vehicules_relais.models import Proprietaire, Vehicule


class ClientTestCase(CTC):
    def setUp(self):
        super().setUp()
        self.administrator = ADSManagerAdministratorFactory()
        self.prefecture = self.administrator.prefecture
        self.commune = CommuneFactory(departement=self.prefecture.numero)
        self.ads_manager = ADSManagerFactory(
            administrator=self.administrator, for_object=self.commune
        )

        self.client_gestionnaire, self.user_gestionnaire = self.create_client()
        self.client_prefecture, self.user_prefecture = self.create_client()
        self.client_inspecteur, self.user_inspecteur = self.create_client()
        self.client_proprietaire, self.user_proprietaire = self.create_client()

        self.request_gestionnaire = ADSManagerRequestFactory(
            user=self.user_gestionnaire, ads_manager=self.ads_manager
        )
        DemandeGestionPrefecture.objects.create(
            user=self.user_prefecture,
            administrator=self.administrator,
            statut=DemandeGestionPrefecture.ACCEPTE,
            accepted_at=datetime.date.today(),
        )
        DemandeAccesLectureSeule.objects.create(
            user=self.user_inspecteur,
            administrator=self.administrator,
            statut=DemandeAccesLectureSeule.ACCEPTE,
        )

        self.proprietaire = Proprietaire.objects.create(nom="Propriétaire")
        self.proprietaire.users.set([self.user_proprietaire])

        self.vehicule = Vehicule.objects.create(
            proprietaire=self.proprietaire,
            departement=self.prefecture,
            immatriculation="123-456-789",
            modele="Peugeot 308",
            motorisation="essence",
            date_mise_circulation=datetime.date(2019, 1, 1),
            nombre_places=4,
            pmr=False,
            commune_localisation=None,
        )


class TestDepartementVehiculesView(ClientTestCase):
    def test_get_200(self):
        test_cases = [
            (self.anonymous_client, 200),
            (self.auth_client, 200),
            (self.admin_client, 200),
            (self.client_gestionnaire, 200),
            (self.client_prefecture, 200),
            (self.client_inspecteur, 200),
            (self.client_proprietaire, 200),
        ]
        for client, expected_response in test_cases:
            with self.subTest(expected_response=expected_response):
                response = client.get(
                    reverse(
                        "vehicules-relais.vehicules_relais_departement",
                        kwargs={"prefecture_id": self.prefecture.id},
                    )
                )
                assert response.status_code == expected_response

    def test_get_filtered_context(self):
        test_cases = [
            (self.anonymous_client, 200),
            (self.auth_client, 200),
            (self.admin_client, 200),
            (self.client_gestionnaire, 200),
            (self.client_prefecture, 200),
            (self.client_inspecteur, 200),
            (self.client_proprietaire, 200),
        ]
        for client, expected_response in test_cases:
            with self.subTest(expected_response=expected_response):
                response = client.get(
                    reverse(
                        "vehicules-relais.vehicules_relais_departement",
                        kwargs={"prefecture_id": self.prefecture.id},
                        query={"immatriculation": self.vehicule.immatriculation},
                    )
                )
                self.assertEqual(response.status_code, expected_response)
                self.assertEqual(response.context["vehicule_list"].count(), 1)
                self.assertQuerySetEqual(
                    response.context["vehicule_list"], [self.vehicule]
                )


class TestDepartementHistoriqueView(ClientTestCase):
    def test_get_200(self):
        test_cases = [
            (self.anonymous_client, 404),
            (self.auth_client, 404),
            (self.admin_client, 200),
            (self.client_gestionnaire, 404),
            (self.client_prefecture, 200),
            (self.client_inspecteur, 200),
            (self.client_proprietaire, 404),
        ]
        for client, expected_response in test_cases:
            with self.subTest(expected_response=expected_response):
                response = client.get(
                    reverse("vehicules-relais.vehicules_relais_history")
                )
                assert response.status_code == expected_response


class TestPrefectureVehiculeView(ClientTestCase):
    def test_get_context(self):
        response = self.client_prefecture.get(
            reverse(
                "vehicules-relais.vehicule_relais_departement_detail",
                kwargs={
                    "prefecture_id": self.administrator.prefecture.id,
                    "numero": self.vehicule.numero,
                },
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["vehicule"], self.vehicule)


class TestVehiculeHistoryView(ClientTestCase):
    def test_get_200(self):
        test_cases = [
            (self.anonymous_client, 404),
            (self.auth_client, 404),
            (self.admin_client, 200),
            (self.client_gestionnaire, 404),
            (self.client_prefecture, 200),
            (self.client_inspecteur, 200),
            (self.client_proprietaire, 404),
        ]

        for client, expected_response in test_cases:
            with self.subTest(expected_response=expected_response):
                response = client.get(
                    reverse(
                        "vehicules-relais.vehicule_relais_departement_detail_history",
                        kwargs={"vehicule_numero": self.vehicule.numero},
                    )
                )
                assert response.status_code == expected_response


class TestVehiculeExportView(ClientTestCase):
    def test_get_200(self):
        response = self.client_prefecture.get(
            reverse(
                "vehicules-relais.vehicules_relais_departement_export",
                kwargs={"prefecture_id": self.prefecture.id},
            )
        )
        assert response.status_code == 200
