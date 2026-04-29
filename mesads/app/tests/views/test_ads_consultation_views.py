from django.urls import reverse

from mesads.app.models import ADS, DemandeAccesLectureSeule
from mesads.unittest import ClientTestCase


class TestConsultationADSSearchView(ClientTestCase):
    def setUp(self):
        super().setUp()
        self.inspecteur_client, self.inspecteur_user = self.create_client()
        DemandeAccesLectureSeule.objects.create(
            user=self.inspecteur_user,
            administrator=self.ads_manager_administrator_35,
            statut=DemandeAccesLectureSeule.ACCEPTE,
        )
        self.ads = ADS.objects.create(
            id="12346",
            ads_manager=self.ads_manager_city35,
            ads_in_use=True,
            immatriculation_plate="FDJR-0D-01",
            owner_name="Chonchon Lantoine",
            owner_siret="123456781012",
            number="456",
        )

    def test_permissions(self):
        for client_name, client, expected_status in (
            ("anonymous", self.anonymous_client, 302),
            ("auth", self.auth_client, 404),
            ("ads_manager 35", self.ads_manager_city35_client, 404),
            ("inspecteur 35", self.inspecteur_client, 200),
        ):
            with self.subTest(client_name=client_name, expected_status=expected_status):
                resp = client.get(reverse("app.consultation_search"))
                self.assertEqual(resp.status_code, expected_status)

    def test_filter_on_administrator(self):
        response = self.inspecteur_client.get(
            reverse(
                "app.consultation_search",
                query={"departement": self.ads_manager_administrator_35.prefecture.id},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual([self.ads], list(response.context["results"]))

    def test_filter_on_commune(self):
        response = self.inspecteur_client.get(
            reverse(
                "app.consultation_search",
                query={"commune": "melesse"},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual([self.ads], list(response.context["results"]))

    def test_filter_on_immatriculation(self):
        response = self.inspecteur_client.get(
            reverse(
                "app.consultation_search",
                query={"immatriculation": "FDJR-0D-01"},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual([self.ads], list(response.context["results"]))

    def test_filter_on_owner_or_conducteur(self):
        response = self.inspecteur_client.get(
            reverse(
                "app.consultation_search",
                query={"conducteur": "antoine chonchon"},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual([self.ads], list(response.context["results"]))

    def test_filter_on_siret(self):
        response = self.inspecteur_client.get(
            reverse(
                "app.consultation_search",
                query={"siret": "123456781012"},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual([self.ads], list(response.context["results"]))

    def test_filter_on_numero(self):
        response = self.inspecteur_client.get(
            reverse(
                "app.consultation_search",
                query={"numero": "456"},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual([self.ads], list(response.context["results"]))


class TestConsultationADSExportPDFView(ClientTestCase):
    def setUp(self):
        super().setUp()
        self.inspecteur_client, self.inspecteur_user = self.create_client()
        DemandeAccesLectureSeule.objects.create(
            user=self.inspecteur_user,
            administrator=self.ads_manager_administrator_35,
            statut=DemandeAccesLectureSeule.ACCEPTE,
        )
        self.ads = ADS.objects.create(
            id="12346",
            ads_manager=self.ads_manager_city35,
            ads_in_use=True,
            immatriculation_plate="FDJR-0D-01",
            owner_name="Chonchon Lantoine",
            owner_siret="123456781012",
            number="456",
        )

    def test_get_pdf(self):
        response = self.inspecteur_client.get(
            reverse(
                "app.consultation_ads_export",
                kwargs={"ads_id": self.ads.id},
            )
        )
        self.assertEqual(response.status_code, 200)

    def test_get_pdf_404(self):
        response = self.inspecteur_client.get(
            reverse(
                "app.consultation_ads_export",
                kwargs={"ads_id": self.ads.id + 1},
            )
        )
        self.assertEqual(response.status_code, 404)
