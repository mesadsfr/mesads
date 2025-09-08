from datetime import datetime

from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile

from mesads.fradm.models import Prefecture

from ..models import (
    ADS,
    ADSManager,
    ADSUser,
)
from ..unittest import ClientTestCase


class TestADSManagerView(ClientTestCase):
    def test_permissions(self):
        for client_name, client, expected_status in (
            ("anonymous", self.anonymous_client, 302),
            ("auth", self.auth_client, 404),
            ("ads_manager 35", self.ads_manager_city35_client, 200),
            ("ads_manager_admin 35", self.ads_manager_administrator_35_client, 200),
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

        prefecture = Prefecture.objects.filter(numero="35").get()
        ads_manager = ADSManager.objects.filter(
            content_type=ContentType.objects.get_for_model(prefecture),
            object_id=prefecture.id,
        ).get()

        resp = self.ads_manager_administrator_35_client.get(
            f"/registre_ads/gestion/{ads_manager.id}/"
        )
        self.assertEqual(
            self.ads_manager_administrator_35.prefecture,
            resp.context["ads_manager"].content_object,
        )

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
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/?q=imm4tricul4tion"
        )
        self.assertEqual(list(resp.context["ads_list"].all()), [ads1])

        # Owner firstname/lastname, returns second ADS
        resp = self.ads_manager_city35_client.get(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/?q=bob dyla"
        )
        self.assertEqual(list(resp.context["ads_list"].all()), [ads2])

        # Owner SIRET, return third ADS
        resp = self.ads_manager_city35_client.get(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/?q=123123123"
        )
        self.assertEqual(list(resp.context["ads_list"].all()), [ads3])

        # User SIRET, return ADS 4
        resp = self.ads_manager_city35_client.get(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/?q=22222222222222"
        )
        self.assertEqual(list(resp.context["ads_list"].all()), [ads4])

        # User name, return ADS 3
        resp = self.ads_manager_city35_client.get(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/?q=Henri SUPER"
        )
        self.assertEqual(list(resp.context["ads_list"].all()), [ads3])

        # CPAM accepted true, return ads 1
        resp = self.ads_manager_city35_client.get(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/?accepted_cpam=True"
        )
        self.assertEqual(list(resp.context["ads_list"].all()), [ads1])

        # CPAM accepted false, return ads 2
        resp = self.ads_manager_city35_client.get(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/?accepted_cpam=False"
        )
        self.assertEqual(list(resp.context["ads_list"].all()), [ads2])

        # CPAM accepted any, and no filters, return all
        resp = self.ads_manager_city35_client.get(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/?q=&accepted_cpam="
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
        # Set the flag "no_ads_declared" for an administration which has ADS registered is impossible
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
            ("ads_manager_admin 35", self.ads_manager_administrator_35_client, 200),
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


class TestADSManagerDecreeView(ClientTestCase):
    def test_permissions(self):
        for client_name, client, expected_status in (
            ("anonymous", self.anonymous_client, 302),
            ("auth", self.auth_client, 404),
            ("ads_manager 35", self.ads_manager_city35_client, 200),
            ("ads_manager_admin 35", self.ads_manager_administrator_35_client, 200),
        ):
            with self.subTest(client_name=client_name, expected_status=expected_status):
                resp = client.get(
                    f"/registre_ads/gestion/{self.ads_manager_city35.id}/arrete"
                )
                self.assertEqual(resp.status_code, expected_status)

    def test_get_404(self):
        resp = self.ads_manager_city35_client.get("/registre_ads/gestion/99999/arrete")
        self.assertEqual(resp.status_code, 404)

    def test_get(self):
        resp = self.ads_manager_city35_client.get(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/arrete"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["ads_manager"], self.ads_manager_city35)

    def test_post(self):
        file1 = SimpleUploadedFile(
            name="myfile.pdf", content=b"First file", content_type="application/pdf"
        )
        file2 = SimpleUploadedFile(
            name="myfile2.pdf", content=b"Second file", content_type="application/pdf"
        )

        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/arrete",
            {
                "adsmanagerdecree_set-TOTAL_FORMS": 5,
                "adsmanagerdecree_set-INITIAL_FORMS": 0,
                "adsmanagerdecree_set-MIN_NUM_FORMS": 0,
                "adsmanagerdecree_set-MAX_NUM_FORMS": 5,
                "adsmanagerdecree_set-0-file": file1,
                "adsmanagerdecree_set-1-file": file2,
            },
        )
        self.assertEqual(resp.status_code, 302)

        ads_manager_decrees = self.ads_manager_city35.adsmanagerdecree_set.all()
        self.assertEqual(len(ads_manager_decrees), 2)
        self.assertEqual(ads_manager_decrees[0].file.read(), b"First file")
        self.assertEqual(ads_manager_decrees[1].file.read(), b"Second file")


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
