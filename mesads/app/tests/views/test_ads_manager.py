from datetime import date, datetime, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from mesads.app.models import (
    ADS,
    ADSManagerDecree,
    ADSUser,
)
from mesads.unittest import ClientTestCase

from ..factories import ADSManagerDecreeFactory


class TestADSManagerView(ClientTestCase):
    def test_permissions(self):
        for client_name, client, expected_status in (
            ("anonymous", self.anonymous_client, 302),
            ("auth", self.auth_client, 404),
            ("ads_manager 35", self.ads_manager_city35_client, 200),
        ):
            with self.subTest(client_name=client_name, expected_status=expected_status):
                resp = client.get(
                    f"/registre_ads/gestion/{self.ads_manager_city35.id}/"
                )
                self.assertEqual(resp.status_code, expected_status)

    def test_get_404(self):
        resp = self.ads_manager_city35_client.get("/registre_ads/gestion/99999/")
        self.assertEqual(resp.status_code, 404)

    def test_get(self):
        resp = self.ads_manager_city35_client.get(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/"
        )
        self.assertEqual(self.ads_manager_city35, resp.context["ads_manager"])

    def test_filters(self):
        """Test filtering"""
        # ADS 1
        ads1 = ADS.objects.create(
            number="FILTER1",
            ads_manager=self.ads_manager_city35,
            immatriculation_plate="imm4tri-cul4tion",
            accepted_cpam=True,
            ads_in_use=True,
        )
        # ADS 2
        ads2 = ADS.objects.create(
            number="FILTER2",
            ads_manager=self.ads_manager_city35,
            owner_name="Bob Dylan",
            accepted_cpam=False,
            ads_in_use=True,
        )
        # ADS 3
        ads3 = ADS.objects.create(
            number="FILTER3",
            ads_manager=self.ads_manager_city35,
            owner_siret="12312312312312",
            ads_in_use=True,
        )
        ADSUser.objects.create(ads=ads3, name="Henri super", siret="11111111111111")
        # ADS 4
        ads4 = ADS.objects.create(
            number="FILTER4", ads_manager=self.ads_manager_city35, ads_in_use=True
        )
        ADSUser.objects.create(
            ads=ads4, name="Matthieu pas super", siret="22222222222222"
        )

        # Immatriculatin plate, returns first ADS
        resp = self.ads_manager_city35_client.get(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/?search=imm4tricul4tion"
        )
        self.assertEqual(list(resp.context["ads_list"].all()), [ads1])

        # Owner firstname/lastname, returns second ADS
        resp = self.ads_manager_city35_client.get(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/?search=bob dyla"
        )
        self.assertEqual(list(resp.context["ads_list"].all()), [ads2])

        # Owner SIRET, return third ADS
        resp = self.ads_manager_city35_client.get(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/?search=123123123"
        )
        self.assertEqual(list(resp.context["ads_list"].all()), [ads3])

        # User SIRET, return ADS 4
        resp = self.ads_manager_city35_client.get(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/?search=22222222222222"
        )
        self.assertEqual(list(resp.context["ads_list"].all()), [ads4])

        # User name, return ADS 3
        resp = self.ads_manager_city35_client.get(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/?search=Henri SUPER"
        )
        self.assertEqual(list(resp.context["ads_list"].all()), [ads3])

        # CPAM accepted true, return ads 1
        resp = self.ads_manager_city35_client.get(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/?accepted_cpam=on"
        )
        self.assertEqual(list(resp.context["ads_list"].all()), [ads1])

        # CPAM accepted any, and no filters, return all
        resp = self.ads_manager_city35_client.get(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/?search=&accepted_cpam="
        )
        self.assertEqual(list(resp.context["ads_list"].all()), [ads1, ads2, ads3, ads4])

    def test_post_ok(self):
        # Set the flag "no_ads_declared" for an administration that has no ADS
        self.assertFalse(self.ads_manager_city35.no_ads_declared)
        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/",
            {
                "no_ads_declared": "on",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.ads_manager_city35.refresh_from_db()
        self.assertTrue(self.ads_manager_city35.no_ads_declared)

        # Remove the flag
        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/",
        )
        self.assertEqual(resp.status_code, 302)
        self.ads_manager_city35.refresh_from_db()
        self.assertFalse(self.ads_manager_city35.no_ads_declared)

    def test_post_error(self):
        # Set the flag "no_ads_declared" for an administration
        # which has ADS registered is impossible
        self.assertFalse(self.ads_manager_city35.no_ads_declared)
        ADS.objects.create(
            number="12346", ads_manager=self.ads_manager_city35, ads_in_use=True
        )
        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/",
            {
                "no_ads_declared": "on",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.ads_manager_city35.refresh_from_db()
        self.assertFalse(self.ads_manager_city35.no_ads_declared)


class TestExportADSManager(ClientTestCase):
    def test_permissions(self):
        for client_name, client, expected_status in (
            ("admin", self.admin_client, 200),
            ("anonymous", self.anonymous_client, 302),
            ("auth", self.auth_client, 404),
            ("ads_manager 35", self.ads_manager_city35_client, 200),
        ):
            with self.subTest(client_name=client_name, expected_status=expected_status):
                resp = client.get(
                    f"/registre_ads/gestion/{self.ads_manager_city35.id}/export"
                )
                self.assertEqual(resp.status_code, expected_status)

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

        resp = self.ads_manager_city35_client.get(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/export"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.headers["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


class TestADSManagerArreteGestion(ClientTestCase):
    def test_update_ok(self):
        today = date.today()
        arrete = ADSManagerDecreeFactory(
            ads_manager=self.ads_manager_city35, date_arrete=today, nombre_ads=5
        )
        data = {"date_arrete": today - timedelta(days=5), "nombre_ads": 6}
        response = self.ads_manager_city35_client.post(
            reverse(
                "app.ads-manager.arrete.update",
                kwargs={
                    "manager_id": self.ads_manager_city35.id,
                    "arrete_id": arrete.id,
                },
            ),
            data,
        )
        assert response.status_code == 302
        arrete.refresh_from_db()
        assert arrete.nombre_ads == data["nombre_ads"]
        assert arrete.date_arrete == data["date_arrete"]

    def test_delete_ok(self):
        today = date.today()
        arrete = ADSManagerDecreeFactory(
            ads_manager=self.ads_manager_city35, date_arrete=today, nombre_ads=5
        )

        response = self.ads_manager_city35_client.post(
            reverse(
                "app.ads-manager.arrete.delete",
                kwargs={
                    "manager_id": self.ads_manager_city35.id,
                    "arrete_id": arrete.id,
                },
            ),
        )
        assert response.status_code == 302
        assert not ADSManagerDecree.objects.filter(id=arrete.id).exists()


class TestADSManagerDecreeView(ClientTestCase):
    def test_permissions(self):
        for client_name, client, expected_status in (
            ("anonymous", self.anonymous_client, 302),
            ("auth", self.auth_client, 404),
            ("ads_manager 35", self.ads_manager_city35_client, 200),
        ):
            with self.subTest(client_name=client_name, expected_status=expected_status):
                resp = client.get(
                    reverse(
                        "app.ads-manager.decree.detail",
                        kwargs={"manager_id": self.ads_manager_city35.id},
                    )
                )
                self.assertEqual(resp.status_code, expected_status)

    def test_get_404(self):
        resp = self.ads_manager_city35_client.get("/registre_ads/gestion/99999/arrete")
        self.assertEqual(resp.status_code, 404)

    def test_get(self):
        resp = self.ads_manager_city35_client.get(
            reverse(
                "app.ads-manager.decree.detail",
                kwargs={"manager_id": self.ads_manager_city35.id},
            )
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["ads_manager"], self.ads_manager_city35)

    def test_post(self):
        file = SimpleUploadedFile(
            name="myfile.pdf",
            content=b"Contenu super fichier",
            content_type="application/pdf",
        )

        self.assertEqual(
            ADSManagerDecree.objects.filter(
                ads_manager=self.ads_manager_city35
            ).count(),
            0,
        )

        resp = self.ads_manager_city35_client.post(
            reverse(
                "app.ads-manager.decree.detail",
                kwargs={"manager_id": self.ads_manager_city35.id},
            ),
            {"file": file, "date_arrete": date.today(), "nombre_ads": 10},
        )
        self.assertEqual(resp.status_code, 200)

        self.assertEqual(
            ADSManagerDecree.objects.filter(
                ads_manager=self.ads_manager_city35
            ).count(),
            1,
        )

        arrete = ADSManagerDecree.objects.filter(
            ads_manager=self.ads_manager_city35
        ).last()
        self.assertEqual(arrete.file.read(), b"Contenu super fichier")
        self.assertEqual(arrete.date_arrete, date.today())
        self.assertEqual(arrete.nombre_ads, 10)


class TestADSManagerAutocompleteView(ClientTestCase):
    def test_get(self):
        resp = self.anonymous_client.get("/gestionnaire_ads/autocomplete?q=bouches")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["results"]), 1)

        resp = self.anonymous_client.get("/gestionnaire_ads/autocomplete?q=MARSEIL")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["results"]), 1)

        resp = self.anonymous_client.get("/gestionnaire_ads/autocomplete?q=13")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["results"]), 2)

        resp = self.anonymous_client.get("/gestionnaire_ads/autocomplete?q=")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["results"]), 10)
