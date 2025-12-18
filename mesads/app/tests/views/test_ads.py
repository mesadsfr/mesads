from django.core import mail
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Q

from mesads.app.models import (
    ADS,
    ADSLegalFile,
    ADSManager,
    ADSManagerAdministrator,
    ADSUpdateLog,
    ADSUser,
    Notification,
)
from mesads.fradm.models import EPCI, Commune
from mesads.unittest import ClientTestCase


class TestADSView(ClientTestCase):
    def setUp(self):
        super().setUp()
        self.ads = ADS.objects.create(
            number="12346", ads_manager=self.ads_manager_city35, ads_in_use=True
        )

    def test_permissions(self):
        for client_name, client, expected_status in (
            ("anonymous", self.anonymous_client, 302),
            ("auth", self.auth_client, 404),
            ("ads_manager 35", self.ads_manager_city35_client, 200),
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

    def test_update(self):
        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}",
            {
                "number": self.ads.id,
                "certify": "true",
                "ads_in_use": "true",
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

    def test_update_with_notification(self):
        # Add admin user to the ADSManagerAdministrator
        self.ads.ads_manager.administrator.users.add(self.admin_user)

        # Setup notification
        Notification.objects.create(
            user=self.admin_user,
            ads_created_or_updated=True,
        )

        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}",
            {
                "number": self.ads.id,
                "certify": "true",
                "ads_in_use": "true",
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
        self.assertEqual(len(mail.outbox), 1)

    def test_update_invalid_ads_users_formset(self):
        """Missing INITIAL_FORMS, MIN_NUM_FORMS and MAX_NUM_FORMS."""
        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}",
            {
                "number": self.ads.id,
                "certify": "true",
                "ads_in_use": "true",
                "owner_name": "Jean-Jacques Goldman",
                "adsuser_set-TOTAL_FORMS": 10,
                "adslegalfile_set-TOTAL_FORMS": 10,
                "adslegalfile_set-INITIAL_FORMS": 0,
                "adslegalfile_set-MIN_NUM_FORMS": 0,
                "adslegalfile_set-MAX_NUM_FORMS": 10,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context["ads_users_formset"].is_valid())
        self.assertTrue(resp.context["ads_legal_files_formset"].is_valid())

    def test_update_invalid_ads_legal_files_formset(self):
        """Missing INITIAL_FORMS, MIN_NUM_FORMS and MAX_NUM_FORMS."""
        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}",
            {
                "number": self.ads.id,
                "certify": "true",
                "ads_in_use": "true",
                "owner_name": "Jean-Jacques Goldman",
                "adsuser_set-TOTAL_FORMS": 10,
                "adsuser_set-INITIAL_FORMS": 0,
                "adsuser_set-MIN_NUM_FORMS": 0,
                "adsuser_set-MAX_NUM_FORMS": 10,
                "adslegalfile_set-TOTAL_FORMS": 10,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["ads_users_formset"].is_valid())
        self.assertFalse(resp.context["ads_legal_files_formset"].is_valid())

    def test_update_ads_not_in_use(self):
        """
        ADS legal files and ads users should be removed
        when the formsets are not provided.
        """
        ADSUser.objects.create(
            ads=self.ads, status="autre", name="Paul", siret="12312312312312"
        )
        ADSLegalFile.objects.create(
            ads=self.ads, file=SimpleUploadedFile("file.pdf", b"Content")
        )

        self.assertEqual(self.ads.adsuser_set.count(), 1)
        self.assertEqual(self.ads.adslegalfile_set.count(), 1)

        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}",
            {
                "number": self.ads.id,
                "certify": "true",
                "ads_in_use": "false",
                "owner_name": "Jean-Jacques Goldman",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            resp.url,
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}",
        )
        self.ads.refresh_from_db()
        self.assertEqual(self.ads.owner_name, "Jean-Jacques Goldman")
        self.assertEqual(self.ads.adsuser_set.count(), 0)
        self.assertEqual(self.ads.adslegalfile_set.count(), 0)

    def test_update_duplicate(self):
        """Update ADS with the id of another ADS."""
        other_ads = ADS.objects.create(
            number="xxx", ads_manager=self.ads_manager_city35, ads_in_use=True
        )
        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}",
            {
                "number": other_ads.number,
                "certify": "true",
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
                "certify": "true",
                "ads_in_use": "true",
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
                "certify": "true",
                "ads_in_use": "true",
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
            (
                "La date de création de l'ADS doit être "
                "antérieure à la date d'attribution."
            ),
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
                "certify": "true",
                "ads_in_use": "true",
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

    def test_update_invalid_ads_user(self):
        """Request change for both ADS and ADSUser, but the ADSUser is invalid:
        the ADS should not be updated, and all the updates should be made in a
        transaction."""
        self.ads.owner_name = "Old name"
        self.ads.save()

        ads_user = ADSUser.objects.create(
            ads=self.ads, status="titulaire_exploitant", license_number="xxx"
        )
        ads_user2 = ADSUser.objects.create(
            ads=self.ads, status="salarie", license_number="yyy"
        )

        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}",
            {
                "number": self.ads.id,
                "certify": "true",
                "ads_in_use": "true",
                "owner_name": "New name",
                "adsuser_set-TOTAL_FORMS": 10,
                "adsuser_set-INITIAL_FORMS": 2,
                "adsuser_set-MIN_NUM_FORMS": 0,
                "adsuser_set-MAX_NUM_FORMS": 10,
                "adsuser_set-0-id": ads_user.id,
                "adsuser_set-0-status": "titulaire_exploitant",
                "adsuser_set-0-license_number": "xxx",
                "adsuser_set-1-id": ads_user2.id,
                "adsuser_set-1-status": "titulaire_exploitant",
                "adsuser_set-1-license_number": "yyy",
                "adslegalfile_set-TOTAL_FORMS": 10,
                "adslegalfile_set-INITIAL_FORMS": 0,
                "adslegalfile_set-MIN_NUM_FORMS": 0,
                "adslegalfile_set-MAX_NUM_FORMS": 10,
            },
        )

        self.assertEqual(resp.status_code, 200)

        self.assertEqual(
            resp.context["ads_users_formset"].non_form_errors(),
            ["Il ne peut y avoir qu'un seul titulaire par ADS."],
        )

        self.ads.refresh_from_db()
        self.assertEqual(self.ads.owner_name, "Old name")

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
                "certify": "true",
                "ads_in_use": "true",
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
                "certify": "true",
                "ads_in_use": "true",
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
                "certify": "true",
                "ads_in_use": "true",
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
                "certify": "true",
                "ads_in_use": "true",
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
        epci_ads = ADS.objects.create(
            number="12346", ads_manager=epci_ads_manager, ads_in_use=True
        )

        # Error, the commune doesn't belong to the same departement than the EPCI
        invalid_commune = Commune.objects.filter(~Q(departement="01")).first()
        resp = self.admin_client.post(
            f"/registre_ads/gestion/{epci_ads_manager.id}/ads/{epci_ads.id}",
            {
                "number": epci_ads.id,
                "certify": "true",
                "ads_in_use": "true",
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
                "certify": "true",
                "epci_commune": valid_commune.id,
                "ads_in_use": "true",
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
                "certify": "true",
                "ads_in_use": "true",
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

    def test_get_incorrect_ads_manager(self):
        """If user requests /registre_ads/gestion/xxx/ads/yyy but xxx is an
        existing ADSManager, but not the one of the ADS, we want to make sure
        the user is redirected to the correct page."""
        commune = Commune.objects.create(
            type_commune="COM",
            insee="xx",
            departement="xx",
            libelle="xx",
        )
        ads_manager = ADSManager.objects.create(
            content_object=commune,
            administrator=ADSManagerAdministrator.objects.first(),
        )
        resp = self.admin_client.get(
            f"/registre_ads/gestion/{ads_manager.id}/ads/{self.ads.id}",
        )
        self.assertEqual(resp.status_code, 301)
        self.assertEqual(
            resp.headers["Location"],
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}",
        )


class TestADSDeleteView(ClientTestCase):
    def setUp(self):
        super().setUp()
        self.ads = ADS.objects.create(
            id="12346", ads_manager=self.ads_manager_city35, ads_in_use=True
        )

    def test_permissions(self):
        for client_name, client, expected_status in (
            ("anonymous", self.anonymous_client, 302),
            ("auth", self.auth_client, 404),
            ("ads_manager 35", self.ads_manager_city35_client, 200),
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

        self.assertEqual(ADS.objects.filter(id=self.ads.id).count(), 0)
        self.assertEqual(ADS.with_deleted.filter(id=self.ads.id).count(), 1)


class TestADSCreateView(ClientTestCase):
    def test_permissions(self):
        for client_name, client, expected_status in (
            ("anonymous", self.anonymous_client, 302),
            ("auth", self.auth_client, 404),
            ("ads_manager 35", self.ads_manager_city35_client, 200),
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
                "certify": "true",
                "ads_in_use": "true",
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
        ads_update_log = ADSUpdateLog.objects.get(ads=ads)
        self.assertFalse(ads_update_log.is_complete)

    def test_create_with_all_fields(self):
        """Verify that the log has the "complete" flag set when all the
        important fields are provided."""
        # Certify not checked
        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/",
            {
                "number": "abcdef",
                "certify": "false",
                "ads_in_use": "true",
                "owner_name": "Bob Marley",
                "owner_siret": "12345678901234",
                "immatriculation_plate": "XXX-XX-XXX",
                "vehicle_compatible_pmr": "true",
                "eco_vehicle": "true",
                "ads_creation_date": "2015-10-01",
                "adsuser_set-TOTAL_FORMS": 10,
                "adsuser_set-INITIAL_FORMS": 0,
                "adsuser_set-MIN_NUM_FORMS": 0,
                "adsuser_set-MAX_NUM_FORMS": 10,
                "adsuser_set-0-id": "",
                "adsuser_set-0-status": "titulaire_exploitant",
                "adsuser_set-0-license_number": "yyy",
                "adslegalfile_set-TOTAL_FORMS": 10,
                "adslegalfile_set-INITIAL_FORMS": 0,
                "adslegalfile_set-MIN_NUM_FORMS": 0,
                "adslegalfile_set-MAX_NUM_FORMS": 10,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            "Vous devez cocher cette case pour valider le formulaire.",
            resp.context["form"].errors["certify"][0],
        )

        # Ok, certify checked
        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/",
            {
                "number": "abcdef",
                "certify": "true",
                "ads_in_use": "true",
                "owner_name": "Bob Marley",
                "owner_siret": "12345678901234",
                "immatriculation_plate": "XXX-XX-XXX",
                "vehicle_compatible_pmr": "true",
                "eco_vehicle": "true",
                "ads_creation_date": "2015-10-01",
                "adsuser_set-TOTAL_FORMS": 10,
                "adsuser_set-INITIAL_FORMS": 0,
                "adsuser_set-MIN_NUM_FORMS": 0,
                "adsuser_set-MAX_NUM_FORMS": 10,
                "adsuser_set-0-id": "",
                "adsuser_set-0-status": "titulaire_exploitant",
                "adsuser_set-0-license_number": "yyy",
                "adslegalfile_set-TOTAL_FORMS": 10,
                "adslegalfile_set-INITIAL_FORMS": 0,
                "adslegalfile_set-MIN_NUM_FORMS": 0,
                "adslegalfile_set-MAX_NUM_FORMS": 10,
            },
        )
        self.assertEqual(resp.status_code, 302)
        ads = ADS.objects.order_by("-id")[0]
        ads_update_log = ADSUpdateLog.objects.get(ads=ads)
        self.assertTrue(ads_update_log.is_complete)

    def test_create_not_certified(self):
        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/",
            {
                "number": "abcdef",
                "certify": "false",
                "ads_in_use": "true",
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
            "Vous devez cocher cette case pour valider le formulaire.",
            resp.context["form"].errors["certify"][0],
        )

    def test_create_duplicate(self):
        """Attempt to create ads with already-existing id."""
        ADS.objects.create(
            number="123", ads_manager=self.ads_manager_city35, ads_in_use=True
        )

        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/",
            {
                "number": "123",
                "certify": "true",
                "ads_in_use": "true",
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
                "certify": "true",
                "ads_in_use": "true",
                "adsuser_set-TOTAL_FORMS": 10,
                "adsuser_set-INITIAL_FORMS": 0,
                "adsuser_set-MIN_NUM_FORMS": 0,
                "adsuser_set-MAX_NUM_FORMS": 10,
                "adsuser_set-0-status": "cooperateur",
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
        self.assertEqual(new_ads_user.status, "cooperateur")
        self.assertEqual(new_ads_user.name, "Paul")
        self.assertEqual(new_ads_user.siret, "12312312312312")

    def test_create_with_two_titulaires(self):
        resp = self.ads_manager_city35_client.post(
            f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/",
            {
                "number": "abcdef",
                "certify": "true",
                "ads_in_use": "true",
                "adsuser_set-TOTAL_FORMS": 10,
                "adsuser_set-INITIAL_FORMS": 0,
                "adsuser_set-MIN_NUM_FORMS": 0,
                "adsuser_set-MAX_NUM_FORMS": 10,
                "adsuser_set-0-status": "titulaire_exploitant",
                "adsuser_set-0-license_number": "yyy",
                "adsuser_set-1-status": "titulaire_exploitant",
                "adsuser_set-1-license_number": "xxx",
                "adslegalfile_set-TOTAL_FORMS": 10,
                "adslegalfile_set-INITIAL_FORMS": 0,
                "adslegalfile_set-MIN_NUM_FORMS": 0,
                "adslegalfile_set-MAX_NUM_FORMS": 10,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.context["ads_users_formset"].non_form_errors(),
            ["Il ne peut y avoir qu'un seul titulaire par ADS."],
        )

    def test_create_new_ads_with_non_titulaire_user(self):
        try:
            self.ads_manager_city35_client.post(
                f"/registre_ads/gestion/{self.ads_manager_city35.id}/ads/",
                {
                    "number": "abcdef",
                    "certify": "true",
                    "ads_in_use": "true",
                    "ads_creation_date": "2015-10-01",
                    "adsuser_set-TOTAL_FORMS": 10,
                    "adsuser_set-INITIAL_FORMS": 0,
                    "adsuser_set-MIN_NUM_FORMS": 0,
                    "adsuser_set-MAX_NUM_FORMS": 10,
                    "adsuser_set-0-status": "salarie",
                    "adsuser_set-0-license_number": "yyy",
                    "adslegalfile_set-TOTAL_FORMS": 10,
                    "adslegalfile_set-INITIAL_FORMS": 0,
                    "adslegalfile_set-MIN_NUM_FORMS": 0,
                    "adslegalfile_set-MAX_NUM_FORMS": 10,
                },
            )
        except ValidationError as exc:
            self.assertEqual(
                exc.message,
                (
                    "Le conducteur doit nécessairement être le titulaire de "
                    "l'ADS (personne physique) pour une ADS créée "
                    "après le 1er octobre 2014."
                ),
            )
        else:
            self.fail("ValidationError not raised")

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
                "certify": "true",
                "ads_in_use": "true",
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


class TestADSHistoryView(ClientTestCase):
    def setUp(self):
        super().setUp()
        self.ads = ADS.objects.create(
            number="12346", ads_manager=self.ads_manager_city35, ads_in_use=True
        )

    def test_permissions(self):
        for client_name, client, expected_status in (
            ("anonymous", self.anonymous_client, 302),
            ("auth", self.auth_client, 404),
            ("ads_manager 35", self.ads_manager_city35_client, 200),
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
