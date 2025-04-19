from datetime import date

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings, TestCase

from django.contrib.contenttypes.models import ContentType

import requests
import requests_mock

from mesads.fradm.models import (
    Commune,
    EPCI,
    Prefecture,
)
from .models import (
    ADS,
    validate_siret,
    ADSLegalFile,
    ADSManager,
    ADSUser,
    ADSUpdateFile,
    ADSManagerDecree,
    Notification,
    get_legal_filename,
    validate_no_ads_declared,
)

from .unittest import ClientTestCase


class TestADSManager(ClientTestCase):
    def test_str(self):
        self.assertIn("commune", str(self.ads_manager_city35))
        self.assertIn("Melesse", str(self.ads_manager_city35))

    def test_validate_no_ads_declared(self):
        self.assertIsNone(validate_no_ads_declared(self.ads_manager_city35, True))
        self.assertIsNone(validate_no_ads_declared(self.ads_manager_city35, False))

        ADS(number="12345", ads_manager=self.ads_manager_city35, ads_in_use=True).save()

        self.assertIsNone(validate_no_ads_declared(self.ads_manager_city35, False))
        self.assertRaises(
            ValidationError, validate_no_ads_declared, self.ads_manager_city35, True
        )

    def test_no_ads_declared_and_epci_delegate(self):
        """Make sure only no_ads_declared or epci_delegate is set, not both"""
        self.ads_manager_city35.no_ads_declared = True
        self.ads_manager_city35.epci_delegate = self.fixtures_epci[0]
        self.assertRaises(
            ValidationError, validate_no_ads_declared, self.ads_manager_city35, True
        )

    def test_human_name(self):
        ads_manager = ADSManager.objects.get(
            content_type=ContentType.objects.get_for_model(Prefecture),
            object_id=self.fixtures_prefectures[0].id,
        )
        self.assertIn("Préfecture", ads_manager.human_name())
        self.assertTrue(self.fixtures_prefectures[0].libelle, ads_manager.human_name())
        self.assertTrue(self.fixtures_prefectures[0].numero, ads_manager.human_name())

        ads_manager = ADSManager.objects.get(
            content_type=ContentType.objects.get_for_model(EPCI),
            object_id=self.fixtures_epci[0].id,
        )
        self.assertIn("EPCI", ads_manager.human_name())
        self.assertTrue(self.fixtures_epci[0].name, ads_manager.human_name())
        self.assertTrue(self.fixtures_epci[0].departement, ads_manager.human_name())

        ads_manager = ADSManager.objects.get(
            content_type=ContentType.objects.get_for_model(Commune),
            object_id=self.fixtures_communes[0].id,
        )
        self.assertIn("Commune", ads_manager.human_name())
        self.assertTrue(self.fixtures_communes[0].libelle, ads_manager.human_name())
        self.assertTrue(self.fixtures_communes[0].insee, ads_manager.human_name())


class TestADSManagerDecree(ClientTestCase):
    def test_str(self):
        ads_manager_decree = ADSManagerDecree(ads_manager=self.ads_manager_city35)
        self.assertIn(str(self.ads_manager_city35.id), str(ads_manager_decree))

    def test_get_filename(self):
        ads_manager_decree = ADSManagerDecree(ads_manager=self.ads_manager_city35)
        filename = ads_manager_decree.get_filename("superfile.txt")
        self.assertIn(
            f"ads_managers_decrees/{self.ads_manager_city35.id} - commune de Melesse/",
            filename,
        )

    def test_exists_in_storage(self):
        ads_legal_file = ADSManagerDecree(
            ads_manager=self.ads_manager_city35,
            file=SimpleUploadedFile("file.pdf", b"File content"),
        )
        self.assertFalse(ads_legal_file.exists_in_storage())

    def test_human_filename(self):
        ads_manager_decree = ADSManagerDecree(
            ads_manager=self.ads_manager_city35,
            file=SimpleUploadedFile("temp", b"File content"),
        )
        ads_manager_decree.file.name = ads_manager_decree.get_filename("whatever.pdf")
        self.assertEqual(ads_manager_decree.human_filename(), "whatever.pdf")


class TestADSManagerRequest(ClientTestCase):
    def test_str(self):
        self.assertIn(
            self.ads_manager_request.user.email, str(self.ads_manager_request)
        )


class TestADSManagerAdministrator(ClientTestCase):
    def test_str(self):
        self.assertIn(
            self.ads_manager_administrator_35.prefecture.libelle,
            str(self.ads_manager_administrator_35),
        )


class TestValidateSiret(TestCase):
    def test_validate_siret(self):
        self.assertRaises(ValidationError, validate_siret, "1234")

        # Insee token not set, no verification
        self.assertIsNone(validate_siret("12345678912345"))

    @override_settings(INSEE_TOKEN="xxx")
    def test_validate_siret_insee(self):
        siret = "12345678901234"
        api_url = f"https://api.insee.fr/api-sirene/3.11/siret/{siret}"

        with requests_mock.Mocker() as m:
            # Setup mock to return return HTTP/200: valid SIRET
            m.get(api_url)
            self.assertIsNone(validate_siret(siret))

            # Setup mock to return return HTTP/404: invalid SIRET
            m.get(api_url, status_code=404)
            self.assertRaises(ValidationError, validate_siret, siret)

            # Setup mock to raise error on connection: SIRET is not checked
            with self.assertLogs(logger="", level="ERROR") as cm:
                m.get(api_url, exc=requests.exceptions.SSLError)
                self.assertIsNone(validate_siret(siret))

            # Setup mock to return return timeout: SIRET is not checked
            with self.assertLogs(logger="", level="ERROR") as cm:
                m.get(api_url, exc=requests.exceptions.ConnectTimeout)
                self.assertIsNone(validate_siret(siret))

            # Setup mock to return unexpected response from INSEE api
            m.get(api_url, status_code=500)
            with self.assertLogs(logger="", level="ERROR") as cm:
                self.assertIsNone(validate_siret(siret))
                self.assertEqual(len(cm.records), 1)

            # "Établissement non diffusable"
            m.get(
                api_url,
                status_code=403,
                json={
                    "header": {
                        "statut": 403,
                        "message": "Établissement non diffusable (50270280600014)",
                    }
                },
            )
            with self.assertNoLogs():
                self.assertIsNone(validate_siret(siret))

            # Rate limit exceeded
            m.get(api_url, status_code=429)
            with self.assertLogs(logger="", level="INFO") as cm:
                self.assertIsNone(validate_siret(siret))
                self.assertEqual(len(cm.records), 1)

            # Invalid JSON, should not raise exception
            m.get(api_url, status_code=403, text="abc")
            with self.assertLogs(logger="", level="ERROR") as cm:
                self.assertIsNone(validate_siret(siret))
                self.assertEqual(len(cm.records), 1)


class TestADS(ClientTestCase):
    def setUp(self):
        super().setUp()
        self.ads = ADS.objects.create(
            number="12346", ads_manager=self.ads_manager_city35, ads_in_use=True
        )

    def test_str(self):
        self.assertIn(str(self.ads.id), str(self.ads))

    def test_get_legal_filename(self):
        legal_file = ADSLegalFile.objects.create(ads=self.ads)
        filename = get_legal_filename(legal_file, "my_filename")
        self.assertIn("my_filename", filename)

    def test_update_when_locked(self):
        self.ads.ads_manager.is_locked = True
        self.assertRaises(ValidationError, self.ads.save)
        self.assertRaises(ValidationError, self.ads.delete)

    def test_new_ads_more_than_one_user(self):
        ADSUser.objects.create(
            ads=self.ads, status="titulaire_exploitant", license_number="Bob"
        )
        ADSUser.objects.create(ads=self.ads, status="salarie", license_number="Bob")

        self.ads.ads_creation_date = date(2015, 12, 11)
        try:
            self.ads.save()
        except ValidationError as exc:
            self.assertEqual(
                exc.message,
                "Un seul exploitant peut être déclaré pour une ADS créée après le 1er octobre 2014.",
            )
        else:
            self.fail("Should have raised a ValidationError")

    def test_new_ads_and_user_is_not_titulaire(self):
        ADSUser.objects.create(ads=self.ads, status="salarie", license_number="Bob")

        self.ads.ads_creation_date = date(2015, 12, 11)
        try:
            self.ads.save()
        except ValidationError as exc:
            self.assertEqual(
                exc.message,
                "Le conducteur doit nécessairement être le titulaire de l'ADS (personne physique) pour une ADS créée après le 1er octobre 2014.",
            )
        else:
            self.fail("Should have raised a ValidationError")

    def test_ads_type(self):
        self.ads.ads_creation_date = date(2015, 12, 11)
        self.assertEqual(self.ads.ads_type(), "Nouvelle ADS")

        self.ads.ads_creation_date = date(2011, 12, 11)
        self.assertEqual(self.ads.ads_type(), "Ancienne ADS")

        self.ads.ads_creation_date = None
        self.assertEqual(self.ads.ads_type(), "")


class TestADSLegalFile(ClientTestCase):
    def setUp(self):
        super().setUp()
        self.ads = ADS.objects.create(
            number="12346", ads_manager=self.ads_manager_city35, ads_in_use=True
        )

    def test_exists_in_storage(self):
        ads_legal_file = ADSLegalFile(
            ads=self.ads, file=SimpleUploadedFile("file.pdf", b"File content")
        )
        self.assertFalse(ads_legal_file.exists_in_storage())

    def test_human_filename(self):
        ads_legal_file = ADSLegalFile(
            ads=self.ads, file=SimpleUploadedFile("temp", b"File content")
        )
        ads_legal_file.file.name = get_legal_filename(ads_legal_file, "xxx.pdf")
        self.assertEqual(ads_legal_file.human_filename(), "xxx.pdf")


class TestADSUser(ClientTestCase):
    def setUp(self):
        super().setUp()
        self.ads = ADS.objects.create(
            number="12346",
            ads_manager=self.ads_manager_city35,
            ads_in_use=True,
        )

    def test_str(self):
        ads_user = ADSUser.objects.create(ads=self.ads, name="Bob")
        self.assertEqual(str(ads_user), "Bob")

    def test_new_ads_several_users(self):
        self.ads.ads_creation_date = date(2015, 12, 11)
        self.ads.save()
        ADSUser.objects.create(
            ads=self.ads, status="titulaire_exploitant", license_number="Bob"
        )
        ads_user = ADSUser(
            ads=self.ads, status="titulaire_exploitant", license_number="Bob2"
        )
        try:
            ads_user.save()
        except ValidationError as exc:
            self.assertEqual(
                exc.message,
                "Un seul exploitant peut être déclaré pour une ADS créée après le 1er octobre 2014.",
            )
        else:
            self.fail("Should have raised a ValidationError")


class TestADSUpdateFile(ClientTestCase):
    def test_str(self):
        ads_update_file = ADSUpdateFile(user=self.admin_user)
        self.assertIn(f"user {self.admin_user.id}", str(ads_update_file))

    def test_get_update_filename(self):
        ads_update_file = ADSUpdateFile(user=self.admin_user)
        filename = ads_update_file.get_update_filename("superfile.txt")
        self.assertIn("ADS_UPDATES", filename)
        self.assertIn(self.admin_user.email, filename)
        self.assertIn("superfile.txt", filename)


class TestNotification(ClientTestCase):
    def test_str(self):
        notification = Notification(user=self.admin_user)
        self.assertIn(self.admin_user.email, str(notification))
