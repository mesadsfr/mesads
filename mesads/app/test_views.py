from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Q
from django.test import RequestFactory
from django.utils import timezone

from mesads.fradm.models import Commune, EPCI, Prefecture

from .models import (
    ADS,
    ADSLegalFile,
    ADSManager,
    ADSManagerRequest,
    ADSUser,
)
from .unittest import ClientTestCase
from .views import DashboardsView, DashboardsDetailView


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
                resp = client.get("/registre_ads/admin_gestion")
                self.assertEqual(resp.status_code, expected_status)

    def test_invalid_action(self):
        resp = self.ads_manager_administrator_35_client.post(
            "/registre_ads/admin_gestion", {"action": "xxx", "request_id": 1}
        )
        self.assertEqual(resp.status_code, 400)

    def test_invalid_request_id(self):
        resp = self.ads_manager_administrator_35_client.post(
            "/registre_ads/admin_gestion", {"action": "accept", "request_id": 12342}
        )
        self.assertEqual(resp.status_code, 404)

    def test_accept(self):
        self.assertEqual(len(mail.outbox), 0)

        resp = self.ads_manager_administrator_35_client.post(
            "/registre_ads/admin_gestion",
            {"action": "accept", "request_id": self.ads_manager_request.id},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/registre_ads/admin_gestion")
        self.ads_manager_request.refresh_from_db()
        self.assertTrue(self.ads_manager_request.accepted)
        self.assertEqual(len(mail.outbox), 1)

    def test_deny(self):
        self.assertEqual(len(mail.outbox), 0)

        resp = self.ads_manager_administrator_35_client.post(
            "/registre_ads/admin_gestion",
            {"action": "deny", "request_id": self.ads_manager_request.id},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/registre_ads/admin_gestion")
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
                "/registre_ads/admin_gestion",
            )
            self.assertEqual(resp.status_code, 200)

            resp = self.ads_manager_administrator_35_client.get(
                "/registre_ads/admin_gestion?sort=name",
            )
            self.assertEqual(resp.status_code, 200)


class TestADSManagerRequestView(ClientTestCase):
    def setUp(self):
        super().setUp()
        self.initial_ads_managers_count = ADSManagerRequest.objects.count()

    def test_permissions(self):
        for client_name, client, expected_status in (
            ("anonymous", self.anonymous_client, 302),
            ("auth", self.auth_client, 200),
            ("ads_manager 35", self.ads_manager_city35_client, 200),
            ("ads_manager_admin 35", self.ads_manager_administrator_35_client, 200),
        ):
            with self.subTest(client_name=client_name, expected_status=expected_status):
                resp = client.get("/registre_ads/gestion")
                self.assertEqual(resp.status_code, expected_status)

    def test_create_request_invalid_id(self):
        """Provide the id of a non-existing object."""
        resp = self.auth_client.post("/registre_ads/gestion", {"commune": 9999})
        self.assertEqual(len(resp.context["form"].errors["__all__"]), 1)

    def test_create_request_commune(self):
        resp = self.auth_client.post(
            "/registre_ads/gestion", {"commune": self.commune_melesse.id}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            ADSManagerRequest.objects.count(), self.initial_ads_managers_count + 1
        )

        # Make sure django message is in the next request
        resp = self.auth_client.get("/registre_ads/gestion")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["messages"]), 1)
        self.assertEqual(list(resp.context["messages"])[0].level, messages.SUCCESS)

        # If there is a ADSManagerAdministrator related to the commune, an email is sent for each member.
        # The base class ClientTestCase configures Melesse to be managed by the ADSManagerAdministrator entry of
        # l'Ille-et-Vilaine.
        self.assertEqual(len(mail.outbox), 1)

        #
        # If we send the same request, a warning message is displayed and no email is sent.
        #
        resp = self.auth_client.post(
            "/registre_ads/gestion", {"commune": self.commune_melesse.id}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            ADSManagerRequest.objects.count(), self.initial_ads_managers_count + 1
        )

        # Check warning message
        resp = self.auth_client.get("/registre_ads/gestion")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["messages"]), 1)
        self.assertEqual(list(resp.context["messages"])[0].level, messages.WARNING)
        # No new email
        self.assertEqual(len(mail.outbox), 1)

    def test_create_request_epci(self):
        epci = EPCI.objects.first()
        resp = self.auth_client.post("/registre_ads/gestion", {"epci": epci.id})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            ADSManagerRequest.objects.count(), self.initial_ads_managers_count + 1
        )

        # Make sure django message is in the next request
        resp = self.auth_client.get("/registre_ads/gestion")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["messages"]), 1)
        self.assertEqual(list(resp.context["messages"])[0].level, messages.SUCCESS)

        #
        # If we send the same request, no object is created and a warning message is displayed.
        #
        resp = self.auth_client.post("/registre_ads/gestion", {"epci": epci.id})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            ADSManagerRequest.objects.count(), self.initial_ads_managers_count + 1
        )

        resp = self.auth_client.get("/registre_ads/gestion")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["messages"]), 1)
        self.assertEqual(list(resp.context["messages"])[0].level, messages.WARNING)

    def test_create_request_prefecture(self):
        prefecture = Prefecture.objects.first()
        resp = self.auth_client.post(
            "/registre_ads/gestion", {"prefecture": prefecture.id}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            ADSManagerRequest.objects.count(), self.initial_ads_managers_count + 1
        )

        # Make sure django message is in the next request
        resp = self.auth_client.get("/registre_ads/gestion")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["messages"]), 1)
        self.assertEqual(list(resp.context["messages"])[0].level, messages.SUCCESS)

        #
        # If we send the same request, no object is created and a warning message is displayed.
        #
        resp = self.auth_client.post(
            "/registre_ads/gestion", {"prefecture": prefecture.id}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            ADSManagerRequest.objects.count(), self.initial_ads_managers_count + 1
        )

        # Make sure django message is in the next request
        resp = self.auth_client.get("/registre_ads/gestion")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["messages"]), 1)
        self.assertEqual(list(resp.context["messages"])[0].level, messages.WARNING)


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
        )
        # ADS 2
        ads2 = ADS.objects.create(
            number="FILTER2",
            ads_manager=self.ads_manager_city35,
            owner_name="Bob Dylan",
            accepted_cpam=False,
        )
        # ADS 3
        ads3 = ADS.objects.create(
            number="FILTER3",
            ads_manager=self.ads_manager_city35,
            owner_siret="12312312312312",
        )
        ADSUser.objects.create(ads=ads3, name="Henri super", siret="11111111111111")
        # ADS 4
        ads4 = ADS.objects.create(number="FILTER4", ads_manager=self.ads_manager_city35)
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
        ADS.objects.create(number="12346", ads_manager=self.ads_manager_city35)
        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/",
            {
                "no_ads_declared": "on",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.ads_manager_city35.refresh_from_db()
        self.assertFalse(self.ads_manager_city35.no_ads_declared)


class TestADSView(ClientTestCase):
    def setUp(self):
        super().setUp()
        self.ads = ADS.objects.create(
            number="12346", ads_manager=self.ads_manager_city35
        )

    def test_permissions(self):
        for client_name, client, expected_status in (
            ("anonymous", self.anonymous_client, 302),
            ("auth", self.auth_client, 404),
            ("ads_manager 35", self.ads_manager_city35_client, 200),
            ("ads_manager_admin 35", self.ads_manager_administrator_35_client, 200),
        ):
            with self.subTest(client_name=client_name, expected_status=expected_status):
                resp = client.get(
                    f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}"
                )
                self.assertEqual(resp.status_code, expected_status)

    def test_get_404(self):
        resp = self.ads_manager_city35_client.get(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/999"
        )
        self.assertEqual(resp.status_code, 404)

    def test_invalid_form(self):
        """ADSUserFormSet is not provided, error should be rendered."""
        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}",
            {
                "number": self.ads.id,
                "owner_name": "Jean-Jacques Goldman",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["formset"].non_form_errors()), 1)

    def test_update(self):
        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}",
            {
                "number": self.ads.id,
                "owner_name": "Jean-Jacques Goldman",
                "adsuser_set-TOTAL_FORMS": 10,
                "adsuser_set-INITIAL_FORMS": 0,
                "adsuser_set-MIN_NUM_FORMS": 0,
                "adsuser_set-MAX_NUM_FORMS": 10,
                "adslegalfile_set-TOTAL_FORMS": 10,
                "adslegalfile_set-INITIAL_FORMS": 0,
                "adslegalfile_set-MIN_NUM_FORMS": 0,
                "adslegalfile_set-MAX_NUM_FORMS": 10,
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            resp.url,
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}",
        )
        self.ads.refresh_from_db()
        self.assertEqual(self.ads.owner_name, "Jean-Jacques Goldman")

    def test_update_duplicate(self):
        """Update ADS with the id of another ADS."""
        other_ads = ADS.objects.create(
            number="xxx", ads_manager=self.ads_manager_city35
        )
        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}",
            {
                "number": other_ads.number,
                "adsuser_set-TOTAL_FORMS": 10,
                "adsuser_set-INITIAL_FORMS": 0,
                "adsuser_set-MIN_NUM_FORMS": 0,
                "adsuser_set-MAX_NUM_FORMS": 10,
                "adslegalfile_set-TOTAL_FORMS": 10,
                "adslegalfile_set-INITIAL_FORMS": 0,
                "adslegalfile_set-MIN_NUM_FORMS": 0,
                "adslegalfile_set-MAX_NUM_FORMS": 10,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            "Une ADS avec ce numéro existe déjà",
            resp.context["form"].errors["__all__"][0],
        )

    def test_strip_ads_charfields(self):
        """Empty string fields should be stripped automatically."""
        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}",
            {
                "number": self.ads.id,
                "owner_name": "  Jean Jaques   ",
                "owner_email": "-",
                "adsuser_set-TOTAL_FORMS": 10,
                "adsuser_set-INITIAL_FORMS": 0,
                "adsuser_set-MIN_NUM_FORMS": 0,
                "adsuser_set-MAX_NUM_FORMS": 10,
                "adslegalfile_set-TOTAL_FORMS": 10,
                "adslegalfile_set-INITIAL_FORMS": 0,
                "adslegalfile_set-MIN_NUM_FORMS": 0,
                "adslegalfile_set-MAX_NUM_FORMS": 10,
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.ads.refresh_from_db()
        self.assertEqual(self.ads.owner_name, "Jean Jaques")
        self.assertEqual(self.ads.owner_email, "")  # dash should be removed

    def test_update_creation_after_attribution(self):
        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}",
            {
                "number": self.ads.number,
                "ads_creation_date": "2015-10-01",
                "attribution_date": "2010-11-04",
                "adsuser_set-TOTAL_FORMS": 10,
                "adsuser_set-INITIAL_FORMS": 0,
                "adsuser_set-MIN_NUM_FORMS": 0,
                "adsuser_set-MAX_NUM_FORMS": 10,
                "adslegalfile_set-TOTAL_FORMS": 10,
                "adslegalfile_set-INITIAL_FORMS": 0,
                "adslegalfile_set-MIN_NUM_FORMS": 0,
                "adslegalfile_set-MAX_NUM_FORMS": 10,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            "La date de création de l'ADS doit être antérieure à la date d'attribution.",
            resp.context["form"].errors["__all__"][0],
        )

    def test_update_ads_user(self):
        """If all the fields of a ADS user are empty, the entry should be
        removed."""
        ads_user = ADSUser.objects.create(
            ads=self.ads, status="autre", name="Paul", siret="12312312312312"
        )

        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}",
            {
                "number": self.ads.id,
                "adsuser_set-TOTAL_FORMS": 10,
                "adsuser_set-INITIAL_FORMS": 1,
                "adsuser_set-MIN_NUM_FORMS": 0,
                "adsuser_set-MAX_NUM_FORMS": 10,
                "adsuser_set-0-id": ads_user.id,
                "adsuser_set-0-status": "",
                "adsuser_set-0-name": "Henri",
                "adsuser_set-0-siret": "",
                "adslegalfile_set-TOTAL_FORMS": 10,
                "adslegalfile_set-INITIAL_FORMS": 0,
                "adslegalfile_set-MIN_NUM_FORMS": 0,
                "adslegalfile_set-MAX_NUM_FORMS": 10,
            },
        )

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(ADSUser.objects.count(), 1)
        self.assertEqual(ADSUser.objects.get().name, "Henri")

    def test_strip_ads_user_charfields(self):
        """If all the fields of a ADS user are empty, the entry should be
        removed."""
        ads_user = ADSUser.objects.create(
            ads=self.ads, status="autre", name="Paul", siret="12312312312312"
        )

        # Fields should be changed during this POST, since the values are not empty
        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}",
            {
                "number": self.ads.id,
                "adsuser_set-TOTAL_FORMS": 10,
                "adsuser_set-INITIAL_FORMS": 1,
                "adsuser_set-MIN_NUM_FORMS": 0,
                "adsuser_set-MAX_NUM_FORMS": 10,
                "adsuser_set-0-id": ads_user.id,
                "adsuser_set-0-status": "",
                "adsuser_set-0-name": "Paul",
                "adsuser_set-0-siret": "12312312312312",
                "adslegalfile_set-TOTAL_FORMS": 10,
                "adslegalfile_set-INITIAL_FORMS": 0,
                "adslegalfile_set-MIN_NUM_FORMS": 0,
                "adslegalfile_set-MAX_NUM_FORMS": 10,
            },
        )

        self.assertEqual(resp.status_code, 302)
        ads_user.refresh_from_db()
        self.assertEqual(ads_user.name, "Paul")
        self.assertEqual(ads_user.siret, "12312312312312")

        # However now they should be stripped
        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}",
            {
                "number": self.ads.id,
                "adsuser_set-TOTAL_FORMS": 10,
                "adsuser_set-INITIAL_FORMS": 1,
                "adsuser_set-MIN_NUM_FORMS": 0,
                "adsuser_set-MAX_NUM_FORMS": 10,
                "adsuser_set-0-id": ads_user.id,
                "adsuser_set-0-status": "",
                "adsuser_set-0-name": "  Paul  ",
                "adsuser_set-0-siret": "-",
                "adslegalfile_set-TOTAL_FORMS": 10,
                "adslegalfile_set-INITIAL_FORMS": 0,
                "adslegalfile_set-MIN_NUM_FORMS": 0,
                "adslegalfile_set-MAX_NUM_FORMS": 10,
            },
        )

        self.assertEqual(resp.status_code, 302)
        ads_user.refresh_from_db()
        # Fields should not have been changed during the previous POST
        self.assertEqual(ads_user.name, "Paul")
        self.assertEqual(ads_user.siret, "")

    def test_update_ads_legal_file(self):
        legal_file = ADSLegalFile.objects.create(
            ads=self.ads, file=SimpleUploadedFile("file.pdf", b"Content")
        )
        new_upload = SimpleUploadedFile("newfile.pdf", b"New content")
        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}",
            {
                "number": self.ads.id,
                "adsuser_set-TOTAL_FORMS": 10,
                "adsuser_set-INITIAL_FORMS": 0,
                "adsuser_set-MIN_NUM_FORMS": 0,
                "adsuser_set-MAX_NUM_FORMS": 10,
                "adslegalfile_set-TOTAL_FORMS": 10,
                "adslegalfile_set-INITIAL_FORMS": 1,
                "adslegalfile_set-MIN_NUM_FORMS": 0,
                "adslegalfile_set-MAX_NUM_FORMS": 10,
                "adslegalfile_set-0-id": legal_file.id,
                "adslegalfile_set-0-file": new_upload,
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(ADSLegalFile.objects.count(), 1)
        self.assertEqual(ADSLegalFile.objects.get().file.read(), b"New content")

    def test_remove_ads_user(self):
        """If all the fields of a ADS user are empty, the entry should be
        removed."""
        ads_user = ADSUser.objects.create(
            ads=self.ads, status="autre", name="Paul", siret="12312312312312"
        )

        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}",
            {
                "number": self.ads.id,
                "adsuser_set-TOTAL_FORMS": 10,
                "adsuser_set-INITIAL_FORMS": 1,
                "adsuser_set-MIN_NUM_FORMS": 0,
                "adsuser_set-MAX_NUM_FORMS": 10,
                "adsuser_set-0-id": ads_user.id,
                "adsuser_set-0-status": "",
                "adsuser_set-0-name": "",
                "adsuser_set-0-siret": "",
                "adsuser_set-0-license-number": "",
                "adslegalfile_set-TOTAL_FORMS": 10,
                "adslegalfile_set-INITIAL_FORMS": 0,
                "adslegalfile_set-MIN_NUM_FORMS": 0,
                "adslegalfile_set-MAX_NUM_FORMS": 10,
            },
        )

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(ADSUser.objects.count(), 0)

    def test_update_epci_commune(self):
        # ADSManager related to the first EPCI in database
        epci_ads_manager = EPCI.objects.filter(departement="01")[0].ads_managers.get()
        epci_ads = ADS.objects.create(number="12346", ads_manager=epci_ads_manager)

        # Error, the commune doesn't belong to the same departement than the EPCI
        invalid_commune = Commune.objects.filter(~Q(departement="01")).first()
        resp = self.admin_client.post(
            f"/registre_ads/gestion/{epci_ads_manager.id}/ads/{epci_ads.id}",
            {
                "number": epci_ads.id,
                "epci_commune": invalid_commune.id,
                "adsuser_set-TOTAL_FORMS": 10,
                "adsuser_set-INITIAL_FORMS": 0,
                "adsuser_set-MIN_NUM_FORMS": 0,
                "adsuser_set-MAX_NUM_FORMS": 10,
                "adslegalfile_set-TOTAL_FORMS": 10,
                "adslegalfile_set-INITIAL_FORMS": 0,
                "adslegalfile_set-MIN_NUM_FORMS": 0,
                "adslegalfile_set-MAX_NUM_FORMS": 10,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            "Ce choix ne fait pas partie de ceux disponibles",
            resp.context["form"].errors["epci_commune"][0],
        )

        valid_commune = Commune.objects.filter(departement="01").first()
        resp = self.admin_client.post(
            f"/registre_ads/gestion/{epci_ads_manager.id}/ads/{epci_ads.id}",
            {
                "number": epci_ads.id,
                "epci_commune": valid_commune.id,
                "adsuser_set-TOTAL_FORMS": 10,
                "adsuser_set-INITIAL_FORMS": 0,
                "adsuser_set-MIN_NUM_FORMS": 0,
                "adsuser_set-MAX_NUM_FORMS": 10,
                "adslegalfile_set-TOTAL_FORMS": 10,
                "adslegalfile_set-INITIAL_FORMS": 0,
                "adslegalfile_set-MIN_NUM_FORMS": 0,
                "adslegalfile_set-MAX_NUM_FORMS": 10,
            },
        )
        self.assertEqual(resp.status_code, 302)

        epci_ads.refresh_from_db()
        self.assertEqual(epci_ads.epci_commune, valid_commune)

    def test_create_ads_user_invalid_siret(self):
        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}",
            {
                "number": self.ads.id,
                "adsuser_set-TOTAL_FORMS": 10,
                "adsuser_set-INITIAL_FORMS": 1,
                "adsuser_set-MIN_NUM_FORMS": 0,
                "adsuser_set-MAX_NUM_FORMS": 10,
                "adsuser_set-0-id": "",
                "adsuser_set-0-status": "",
                "adsuser_set-0-name": "",
                "adsuser_set-0-siret": "1234",
                "adsuser_set-0-license_number": "",
                "adslegalfile_set-TOTAL_FORMS": 10,
                "adslegalfile_set-INITIAL_FORMS": 0,
                "adslegalfile_set-MIN_NUM_FORMS": 0,
                "adslegalfile_set-MAX_NUM_FORMS": 10,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            ["Un SIRET doit être composé de 14 numéros"],
            resp.context["ads_users_formset"].forms[0].errors["siret"],
        )
        self.assertEqual(ADSUser.objects.count(), 0)


class TestADSDeleteView(ClientTestCase):
    def setUp(self):
        super().setUp()
        self.ads = ADS.objects.create(id="12346", ads_manager=self.ads_manager_city35)

    def test_permissions(self):
        for client_name, client, expected_status in (
            ("anonymous", self.anonymous_client, 302),
            ("auth", self.auth_client, 404),
            ("ads_manager 35", self.ads_manager_city35_client, 200),
            ("ads_manager_admin 35", self.ads_manager_administrator_35_client, 200),
        ):
            with self.subTest(client_name=client_name, expected_status=expected_status):
                resp = client.get(
                    f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}/delete"
                )
                self.assertEqual(resp.status_code, expected_status)

    def test_get_404(self):
        resp = self.ads_manager_city35_client.get(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/999/delete"
        )
        self.assertEqual(resp.status_code, 404)

    def test_delete(self):
        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}/delete",
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            resp.url, f"/registre_ads/gestion/{self.ads_manager_city35.id}/"
        )
        self.assertRaises(ADS.DoesNotExist, self.ads.refresh_from_db)


class TestADSCreateView(ClientTestCase):
    def test_permissions(self):
        for client_name, client, expected_status in (
            ("anonymous", self.anonymous_client, 302),
            ("auth", self.auth_client, 404),
            ("ads_manager 35", self.ads_manager_city35_client, 200),
            ("ads_manager_admin 35", self.ads_manager_administrator_35_client, 200),
        ):
            with self.subTest(client_name=client_name, expected_status=expected_status):
                resp = client.get(
                    f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/"
                )
                self.assertEqual(resp.status_code, expected_status)

    def test_create_invalid(self):
        """It is impossible to create an ADS if the flag no_ads_declared is set."""
        self.ads_manager_city35.no_ads_declared = True
        self.ads_manager_city35.save()
        resp = self.ads_manager_city35_client.get(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/"
        )
        self.assertEqual(resp.status_code, 404)

    def test_create(self):
        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/",
            {
                "number": "abcdef",
                "adsuser_set-TOTAL_FORMS": 10,
                "adsuser_set-INITIAL_FORMS": 0,
                "adsuser_set-MIN_NUM_FORMS": 0,
                "adsuser_set-MAX_NUM_FORMS": 10,
                "adslegalfile_set-TOTAL_FORMS": 10,
                "adslegalfile_set-INITIAL_FORMS": 0,
                "adslegalfile_set-MIN_NUM_FORMS": 0,
                "adslegalfile_set-MAX_NUM_FORMS": 10,
            },
        )
        self.assertEqual(resp.status_code, 302)
        ads = ADS.objects.order_by("-id")[0]
        self.assertEqual(
            resp.url, f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{ads.id}"
        )

    def test_create_duplicate(self):
        """Attempt to create ads with already-existing id."""
        ADS.objects.create(number="123", ads_manager=self.ads_manager_city35)

        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/",
            {
                "number": "123",
                "adsuser_set-TOTAL_FORMS": 10,
                "adsuser_set-INITIAL_FORMS": 0,
                "adsuser_set-MIN_NUM_FORMS": 0,
                "adsuser_set-MAX_NUM_FORMS": 10,
                "adslegalfile_set-TOTAL_FORMS": 10,
                "adslegalfile_set-INITIAL_FORMS": 0,
                "adslegalfile_set-MIN_NUM_FORMS": 0,
                "adslegalfile_set-MAX_NUM_FORMS": 10,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            "Une ADS avec ce numéro existe déjà",
            resp.context["form"].errors["number"][0],
        )

    def test_create_with_ads_user(self):
        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/",
            {
                "number": "abcdef",
                "adsuser_set-TOTAL_FORMS": 10,
                "adsuser_set-INITIAL_FORMS": 0,
                "adsuser_set-MIN_NUM_FORMS": 0,
                "adsuser_set-MAX_NUM_FORMS": 10,
                "adsuser_set-0-status": "autre",
                "adsuser_set-0-name": "Paul",
                "adsuser_set-0-siret": "12312312312312",
                "adslegalfile_set-TOTAL_FORMS": 10,
                "adslegalfile_set-INITIAL_FORMS": 0,
                "adslegalfile_set-MIN_NUM_FORMS": 0,
                "adslegalfile_set-MAX_NUM_FORMS": 10,
            },
        )
        self.assertEqual(resp.status_code, 302)
        ads = ADS.objects.order_by("-id")[0]
        self.assertEqual(
            resp.url, f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{ads.id}"
        )

        self.assertEqual(ADSUser.objects.count(), 1)
        new_ads_user = ADSUser.objects.get()
        self.assertEqual(new_ads_user.status, "autre")
        self.assertEqual(new_ads_user.name, "Paul")
        self.assertEqual(new_ads_user.siret, "12312312312312")

    def test_create_with_legal_files(self):
        legal_file1 = SimpleUploadedFile(
            name="myfile.pdf", content=b"First file", content_type="application/pdf"
        )
        legal_file2 = SimpleUploadedFile(
            name="myfile2.pdf", content=b"Second file", content_type="application/pdf"
        )

        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/",
            {
                "number": "abcdef",
                "adsuser_set-TOTAL_FORMS": 10,
                "adsuser_set-INITIAL_FORMS": 0,
                "adsuser_set-MIN_NUM_FORMS": 0,
                "adsuser_set-MAX_NUM_FORMS": 10,
                "adslegalfile_set-TOTAL_FORMS": 10,
                "adslegalfile_set-INITIAL_FORMS": 0,
                "adslegalfile_set-MIN_NUM_FORMS": 0,
                "adslegalfile_set-MAX_NUM_FORMS": 10,
                "adslegalfile_set-0-file": legal_file1,
                "adslegalfile_set-1-file": legal_file2,
            },
        )
        self.assertEqual(resp.status_code, 302)
        ads = ADS.objects.order_by("-id")[0]
        self.assertEqual(
            resp.url, f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{ads.id}"
        )

        self.assertEqual(ADSLegalFile.objects.count(), 2)
        legal_files = ADSLegalFile.objects.order_by("id")

        self.assertEqual(legal_files[0].file.read(), b"First file")
        self.assertEqual(legal_files[1].file.read(), b"Second file")


class TestExport(ClientTestCase):
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
            number="1", ads_manager=self.ads_manager_city35, accepted_cpam=True
        )
        ADS.objects.create(number="2", ads_manager=self.ads_manager_city35)
        ADS.objects.create(
            number="3",
            ads_manager=self.ads_manager_city35,
            ads_creation_date=datetime.now().date(),
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
            number="1", ads_manager=self.ads_manager_city35, accepted_cpam=True
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
            number="1", ads_manager=self.ads_manager_city35, accepted_cpam=True
        )
        resp = self.ads_manager_administrator_35_client.get(
            f"/registre_ads/prefectures/{self.ads_manager_administrator_35.prefecture.id}/export"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.headers["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


class TestDashboardsViews(ClientTestCase):
    """Test DashboardsView and DashboardsDetailView"""

    def setUp(self):
        super().setUp()
        request = RequestFactory().get("/dashboards")
        self.dashboards_view = DashboardsView()
        self.dashboards_view.setup(request)

        request = RequestFactory().get(
            f"/registre_ads/dashboards/{self.ads_manager_administrator_35.id}"
        )
        self.dashboards_detail_view = DashboardsDetailView(
            object=self.ads_manager_administrator_35
        )
        self.dashboards_detail_view.setup(request)

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

                resp = client.get(
                    f"/registre_ads/dashboards/{self.ads_manager_administrator_35.id}/"
                )
                self.assertEqual(resp.status_code, expected_status)

    def test_stats_default(self):
        # The base class ClientTestCase creates ads_manager_administrator for
        # departement 35, and configures an ADSManager for the city fo Melesse.
        stats = [
            {
                "obj": self.ads_manager_administrator_35,
                "ads": {},
                "users": {
                    "now": 1,
                },
            }
        ]
        stats_total = {
            "ads": {
                "now": 0,
                "with_info_now": 0,
                "3_months": 0,
                "6_months": 0,
                "12_months": 0,
            },
            "users": {
                "now": 1,
                "3_months": 0,
                "6_months": 0,
                "12_months": 0,
            },
        }
        self.assertEqual((stats, stats_total), self.dashboards_view.get_stats())

        self.assertEqual(
            [
                {
                    "obj": self.ads_manager_city35,
                    "ads": {},
                    "users": {
                        "now": 1,
                    },
                }
            ],
            self.dashboards_detail_view.get_stats(),
        )

    def test_stats_for_several_ads(self):
        # Create several ADS for the city of Melesse
        now = timezone.now()
        for idx, creation_date in enumerate(
            [
                now - timedelta(days=365 * 2),  # 2 years old ADS
                now - timedelta(days=300),  # > 6 && < 12 months old
                now - timedelta(days=120),  # > 3 && < 6 months old
                now - timedelta(days=1),  # yesterday
            ]
        ):
            ads = ADS.objects.create(
                number=str(idx), ads_manager=self.ads_manager_city35
            )
            ads.creation_date = creation_date
            ads.save()

        stats = [
            {
                "obj": self.ads_manager_administrator_35,
                "ads": {
                    "now": 4,
                    "3_months": 3,
                    "6_months": 2,
                    "12_months": 1,
                },
                "users": {
                    "now": 1,
                },
            }
        ]
        stats_total = {
            "ads": {
                "now": 4,
                "with_info_now": 0,
                "3_months": 3,
                "6_months": 2,
                "12_months": 1,
            },
            "users": {
                "now": 1,
                "3_months": 0,
                "6_months": 0,
                "12_months": 0,
            },
        }

        self.assertEqual((stats, stats_total), self.dashboards_view.get_stats())

        self.assertEqual(
            [
                {
                    "obj": self.ads_manager_city35,
                    "ads": {
                        "now": 4,
                        "3_months": 3,
                        "6_months": 2,
                        "12_months": 1,
                    },
                    "users": {
                        "now": 1,
                    },
                }
            ],
            self.dashboards_detail_view.get_stats(),
        )

    def test_stats_for_several_ads_managers(self):
        now = timezone.now()
        # Give administration permissions for several users to Melesse.
        for creation_date in [
            now - timedelta(days=365 * 2),  # 2 years old ADS
            now - timedelta(days=300),  # > 6 && < 12 months old
            now - timedelta(days=120),  # > 3 && < 6 months old
            now - timedelta(days=1),  # yesterday
        ]:
            user = self.create_user().obj
            ads_manager_request = ADSManagerRequest.objects.create(
                user=user,
                ads_manager=self.ads_manager_city35,
                accepted=True,
            )
            ads_manager_request.created_at = creation_date
            ads_manager_request.save()

        stats = [
            {
                "obj": self.ads_manager_administrator_35,
                "ads": {},
                "users": {
                    "now": 5,
                    "3_months": 3,
                    "6_months": 2,
                    "12_months": 1,
                },
            }
        ]
        stats_total = {
            "ads": {
                "now": 0,
                "with_info_now": 0,
                "3_months": 0,
                "6_months": 0,
                "12_months": 0,
            },
            "users": {
                "now": 5,
                "3_months": 3,
                "6_months": 2,
                "12_months": 1,
            },
        }

        self.assertEqual((stats, stats_total), self.dashboards_view.get_stats())

        self.assertEqual(
            [
                {
                    "obj": self.ads_manager_city35,
                    "ads": {},
                    "users": {
                        "now": 5,
                        "3_months": 3,
                        "6_months": 2,
                        "12_months": 1,
                    },
                }
            ],
            self.dashboards_detail_view.get_stats(),
        )


class TestFAQView(ClientTestCase):
    def test_get(self):
        resp = self.client.get("/faq")
        self.assertEqual(resp.status_code, 200)


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


class TestADSDecreeView(ClientTestCase):
    def setUp(self):
        super().setUp()
        self.ads = ADS.objects.create(
            number="12346", ads_manager=self.ads_manager_city35
        )
        self.mgt_form_current_step_name = (
            f"ads_decree_view_{self.ads.id}_{self.ads_manager_city35.id}-current_step"
        )

    def test_permissions(self):
        for client_name, client, expected_status in (
            ("anonymous", self.anonymous_client, 302),
            ("auth", self.auth_client, 404),
            ("ads_manager 35", self.ads_manager_city35_client, 200),
            ("ads_manager_admin 35", self.ads_manager_administrator_35_client, 200),
        ):
            with self.subTest(client_name=client_name, expected_status=expected_status):
                resp = client.get(
                    f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}/arrete"
                )
                self.assertEqual(resp.status_code, expected_status)

    def test_get(self):
        resp = self.ads_manager_city35_client.get(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}/arrete"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["wizard"]["steps"].index, 0)

    def _step_0(self, is_old_ads):
        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}/arrete",
            {
                self.mgt_form_current_step_name: "0",
                "0-is_old_ads": is_old_ads,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["wizard"]["steps"].index, 1)
        return resp

    def _step_1(self, decree_creation_reason="change_vehicle"):
        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}/arrete",
            {
                self.mgt_form_current_step_name: "1",
                "1-decree_creation_reason": decree_creation_reason,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["wizard"]["steps"].index, 2)
        return resp

    def _step_2(self, overrides=None, check_going_to_next_step=True):
        params = {
            self.mgt_form_current_step_name: "2",
            "2-decree_number": "0001/2023",
            "2-decree_creation_date": "2023-05-12",
            "2-decree_commune": self.ads_manager_city35.content_object.libelle,
            "2-decree_limiting_ads_number": "0002/2023",
            "2-decree_limiting_ads_date": "1998-05-25",
            "2-ads_owner": "Bob Marley",
            "2-ads_owner_rcs": "123",
            "2-tenant_legal_representative": "Bob Marley",
            "2-tenant_signature_date": "2023-06-02",
            "2-tenant_ads_user": "Mireille Mathieu",
            "2-ads_end_date": "2028-05-12",
            "2-ads_number": "1",
            "2-vehicle_brand": "Peugeot",
            "2-vehicle_model": "208",
            "2-immatriculation_plate": "YD-YTA-35",
            "2-previous_decree_number": "0003/2023",
            "2-previous_decree_date": "2023-06-02",
            "2-decree_number_taxi_activity": "0004/2023",
        }
        if overrides:
            params.update(overrides)
        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}/arrete",
            params,
        )
        self.assertEqual(resp.status_code, 200)
        if check_going_to_next_step:
            self.assertEqual(resp.context["wizard"]["steps"].index, 3)
        return resp

    def _step_3(self):
        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}/arrete",
            {
                self.mgt_form_current_step_name: "3",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["Content-Type"], "application/vnd.openxmlformats")
        # .docx documents start with 0x504b0304
        self.assertEqual(resp.content[0], 0x50)
        self.assertEqual(resp.content[1], 0x4B)
        self.assertEqual(resp.content[2], 0x03)
        self.assertEqual(resp.content[3], 0x04)
        return resp

    def _step_back(self, goto_step):
        current_step = str(goto_step + 1)
        goto_step = str(goto_step)

        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}/arrete",
            {
                self.mgt_form_current_step_name: current_step,
                "wizard_goto_step": goto_step,
            },
        )
        self.assertEqual(resp.status_code, 200)
        return resp

    def test_generate_old_ads(self):
        self._step_0(is_old_ads=True)
        self._step_1()
        self._step_2()
        self._step_3()

    def test_generate_new_ads(self):
        self._step_0(is_old_ads=False)
        self._step_1()
        self._step_2()
        self._step_3()

    def test_third_step_decree_number_error(self):
        self._step_0(is_old_ads=True)
        self._step_1()
        # Invalid decree number
        resp = self._step_2(
            overrides={"2-decree_number": "abcdef"}, check_going_to_next_step=False
        )
        self.assertEqual(
            resp.context["form"].errors["decree_number"],
            ["Le champ doit être sous la forme XXXX/2024"],
        )

    def test_third_step_fields_dependencies(self):
        """If previous_decree_number is set, previous_decree_number must be set too"""
        self._step_0(is_old_ads=True)
        self._step_1()
        # Invalid decree number
        resp = self._step_2(
            overrides={
                "2-previous_decree_number": "0003/2023",
                "2-previous_decree_date": "",
            },
            check_going_to_next_step=False,
        )
        self.assertEqual(
            resp.context["form"].errors["previous_decree_date"],
            [
                "Veuillez saisir la date de l'arrêté municipal précédent celui en cours de promulgation"
            ],
        )

    def test_back_navigation(self):
        """This tests CustomCookieWizardView.render_next_step: if the user goes
        to a previous step, storage should be cleared for the next steps to
        avoid errors when going forward again.
        """
        self._step_0(is_old_ads=True)
        self._step_1(decree_creation_reason="rental")
        self._step_2()
        self._step_back(1)
        self._step_back(0)
        resp = self._step_0(is_old_ads=False)
        self.assertFalse(resp.context["form"].is_valid())


class TestADSHistoryView(ClientTestCase):
    def setUp(self):
        super().setUp()
        self.ads = ADS.objects.create(
            number="12346", ads_manager=self.ads_manager_city35
        )

    def test_permissions(self):
        for client_name, client, expected_status in (
            ("anonymous", self.anonymous_client, 302),
            ("auth", self.auth_client, 404),
            ("ads_manager 35", self.ads_manager_city35_client, 200),
            ("ads_manager_admin 35", self.ads_manager_administrator_35_client, 200),
        ):
            with self.subTest(client_name=client_name, expected_status=expected_status):
                resp = client.get(
                    f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}/history"
                )
                self.assertEqual(resp.status_code, expected_status)

    def test_get(self):
        resp = self.ads_manager_city35_client.get(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}/history"
        )
        self.assertEqual(resp.status_code, 200)


class TestStatsView(ClientTestCase):
    def test_get(self):
        resp = self.anonymous_client.get("/chiffres-cles")
        self.assertEqual(resp.status_code, 200)
