import datetime
import http
import logging

from dateutil.relativedelta import relativedelta
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from mesads.app.forms import (
    ArchivageInscriptionListeAttenteForm,
    ContactInscriptionListeAttenteForm,
    InscriptionListeAttenteForm,
    UpdateDelaiInscriptionListeAttenteForm,
)
from mesads.app.models import (
    ADS,
    WAITING_LIST_UNIQUE_ERROR_MESSAGE,
    ADSLegalFile,
    ADSUpdateLog,
    ADSUser,
    InscriptionListeAttente,
)
from mesads.users.unittest import ClientTestCase as BaseClientTestCase

from ..factories import (
    ADSFactory,
    ADSManagerFactory,
    ADSManagerRequestFactory,
    InscriptionListeAttenteFactory,
)


class ClientTestCase(BaseClientTestCase):
    def setUp(self):
        super().setUp()
        self.client, self.user = self.create_client()
        self.ads_manager = ADSManagerFactory(for_commune=True)
        self.ads_manager_request = ADSManagerRequestFactory(
            user=self.user, ads_manager=self.ads_manager
        )
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        # Enable logging
        logging.disable(logging.NOTSET)


class TestListeAttenteView(ClientTestCase):
    def test_get_liste_attente(self):
        inscription = InscriptionListeAttenteFactory(ads_manager=self.ads_manager)
        other_ads_manager = ADSManagerFactory(for_commune=True)
        other_inscription = InscriptionListeAttenteFactory(
            ads_manager=other_ads_manager
        )
        inscription_archived = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager
        )
        inscription_archived.delete()
        inscription_archived.refresh_from_db()

        response = self.client.get(
            reverse("app.liste_attente", kwargs={"manager_id": self.ads_manager.id})
        )
        self.assertIn(inscription, response.context["inscriptions"])
        self.assertNotIn(other_inscription, response.context["inscriptions"])
        self.assertNotIn(inscription_archived, response.context["inscriptions"])
        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertTemplateUsed(response, "pages/ads_register/liste_attente.html")

    def test_get_liste_attente_search(self):
        inscription_1 = InscriptionListeAttenteFactory(ads_manager=self.ads_manager)
        inscription_2 = InscriptionListeAttenteFactory(ads_manager=self.ads_manager)
        inscription_3 = InscriptionListeAttenteFactory(ads_manager=self.ads_manager)

        q_params = f"?search={inscription_1.nom}+{inscription_1.prenom}"

        base_url = reverse(
            "app.liste_attente", kwargs={"manager_id": self.ads_manager.id}
        )

        response = self.client.get(f"{base_url}{q_params}")
        self.assertIn(inscription_1, response.context["inscriptions"])
        self.assertNotIn(inscription_2, response.context["inscriptions"])
        self.assertNotIn(inscription_3, response.context["inscriptions"])
        self.assertEqual(response.status_code, http.HTTPStatus.OK)


class TestListeAttenteArchivesView(ClientTestCase):
    def test_get_liste_attente_archives(self):
        inscription = InscriptionListeAttenteFactory(ads_manager=self.ads_manager)
        other_ads_manager = ADSManagerFactory(for_commune=True)
        other_inscription = InscriptionListeAttenteFactory(
            ads_manager=other_ads_manager
        )
        inscription_archived = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager
        )
        other_inscription_archived = InscriptionListeAttenteFactory(
            ads_manager=other_ads_manager
        )
        inscription_archived.delete()
        inscription_archived.refresh_from_db()
        other_inscription_archived.delete()
        other_inscription_archived.refresh_from_db()

        response = self.client.get(
            reverse(
                "app.liste_attente_archives", kwargs={"manager_id": self.ads_manager.id}
            )
        )
        self.assertIn(inscription_archived, response.context["inscriptions"])
        self.assertNotIn(other_inscription, response.context["inscriptions"])
        self.assertNotIn(other_inscription_archived, response.context["inscriptions"])
        self.assertNotIn(inscription, response.context["inscriptions"])
        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertTemplateUsed(
            response, "pages/ads_register/liste_attente_archivees.html"
        )

    def test_get_liste_attente_archives_search(self):
        inscription_archived = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager
        )
        other_inscription_archived = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager
        )
        inscription_archived.delete()
        inscription_archived.refresh_from_db()
        other_inscription_archived.delete()
        other_inscription_archived.refresh_from_db()

        q_params = f"?search={inscription_archived.nom}+{inscription_archived.prenom}"
        base_url = reverse(
            "app.liste_attente_archives", kwargs={"manager_id": self.ads_manager.id}
        )

        response = self.client.get(f"{base_url}{q_params}")
        self.assertIn(inscription_archived, response.context["inscriptions"])
        self.assertNotIn(other_inscription_archived, response.context["inscriptions"])
        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertTemplateUsed(
            response, "pages/ads_register/liste_attente_archivees.html"
        )


class TestCreationInscriptionListeAttenteView(ClientTestCase):
    def test_get_formulaire_creation_inscription(self):
        response = self.client.get(
            reverse(
                "app.liste_attente_inscription",
                kwargs={"manager_id": self.ads_manager.id},
            )
        )
        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertTemplateUsed(
            response, "pages/ads_register/liste_attente_inscription.html"
        )
        self.assertIsInstance(response.context["form"], InscriptionListeAttenteForm)

    def test_post_formulaire_creation_inscription_ok(self):
        self.assertEqual(InscriptionListeAttente.objects.count(), 0)
        today = datetime.date.today()
        response = self.client.post(
            reverse(
                "app.liste_attente_inscription",
                kwargs={"manager_id": self.ads_manager.id},
            ),
            data={
                "numero": "2",
                "nom": "John",
                "prenom": "Doe",
                "numero_licence": "1234ABCD",
                "numero_telephone": "0606060606",
                "email": "john.doe@test.com",
                "adresse": "10 Rue du test",
                "date_depot_inscription": today,
                "date_dernier_renouvellement": "",
            },
        )
        self.assertEqual(InscriptionListeAttente.objects.count(), 1)
        self.assertEqual(response.status_code, http.HTTPStatus.FOUND)
        inscription = InscriptionListeAttente.objects.last()
        self.assertEqual(inscription.ads_manager, self.ads_manager)
        self.assertIsNone(inscription.date_dernier_renouvellement)
        self.assertEqual(
            inscription.date_fin_validite,
            today + relativedelta(years=1),
        )

    def test_post_formulaire_creation_inscription_with_date_renouvellement(self):
        self.assertEqual(InscriptionListeAttente.objects.count(), 0)
        today = datetime.date.today()
        response = self.client.post(
            reverse(
                "app.liste_attente_inscription",
                kwargs={"manager_id": self.ads_manager.id},
            ),
            data={
                "numero": "1",
                "nom": "John",
                "prenom": "Doe",
                "numero_licence": "1234ABCD",
                "numero_telephone": "0606060606",
                "email": "john.doe@test.com",
                "adresse": "10 Rue du test",
                "date_depot_inscription": today - relativedelta(years=1),
                "date_dernier_renouvellement": today,
            },
        )
        self.assertEqual(InscriptionListeAttente.objects.count(), 1)
        self.assertEqual(response.status_code, http.HTTPStatus.FOUND)
        inscription = InscriptionListeAttente.objects.last()
        self.assertEqual(inscription.ads_manager, self.ads_manager)
        self.assertEqual(
            inscription.date_fin_validite,
            today + relativedelta(years=1),
        )

    def test_post_formulaire_creation_inscription_with_expired_date_depot(self):
        today = datetime.date.today()
        self.assertEqual(InscriptionListeAttente.objects.count(), 0)
        response = self.client.post(
            reverse(
                "app.liste_attente_inscription",
                kwargs={"manager_id": self.ads_manager.id},
            ),
            data={
                "numero": "1",
                "nom": "John",
                "prenom": "Doe",
                "numero_licence": "1234ABCD",
                "numero_telephone": "0606060606",
                "email": "john.doe@test.com",
                "adresse": "10 Rue du test",
                "date_depot_inscription": today - relativedelta(years=2),
                "date_dernier_renouvellement": "",
            },
        )
        self.assertEqual(InscriptionListeAttente.objects.count(), 0)
        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertEqual(
            response.context["form"].errors["date_dernier_renouvellement"],
            [InscriptionListeAttenteForm.ERROR_DATE_RENOUVELLEMENT_EMPTY],
        )

    def test_post_formulaire_creation_inscription_numero_invalide(self):
        inscription = InscriptionListeAttenteFactory(ads_manager=self.ads_manager)
        today = datetime.date.today()
        self.assertEqual(InscriptionListeAttente.objects.count(), 1)
        response = self.client.post(
            reverse(
                "app.liste_attente_inscription",
                kwargs={"manager_id": self.ads_manager.id},
            ),
            data={
                "numero": inscription.numero,
                "nom": "John",
                "prenom": "Doe",
                "numero_licence": "1234ABCD",
                "numero_telephone": "0606060606",
                "email": "john.doe@test.com",
                "adresse": "10 Rue du test",
                "date_depot_inscription": today - relativedelta(years=2),
                "date_dernier_renouvellement": today - relativedelta(months=3),
            },
        )
        self.assertEqual(InscriptionListeAttente.objects.count(), 1)
        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertFalse(response.context["form"].is_valid())
        self.assertEqual(
            response.context["form"].errors["numero"],
            [WAITING_LIST_UNIQUE_ERROR_MESSAGE],
        )

    def test_post_formulaire_creation_inscription_numero_valide(self):
        inscription = InscriptionListeAttenteFactory(ads_manager=self.ads_manager)
        inscription.delete()
        today = datetime.date.today()

        self.assertEqual(InscriptionListeAttente.objects.count(), 0)
        self.assertEqual(InscriptionListeAttente.with_deleted.count(), 1)

        response = self.client.post(
            reverse(
                "app.liste_attente_inscription",
                kwargs={"manager_id": self.ads_manager.id},
            ),
            data={
                "numero": inscription.numero,
                "nom": "John",
                "prenom": "Doe",
                "numero_licence": "1234ABCD",
                "numero_telephone": "0606060606",
                "email": "john.doe@test.com",
                "adresse": "10 Rue du test",
                "date_depot_inscription": today - relativedelta(years=2),
                "date_dernier_renouvellement": today - relativedelta(months=3),
            },
        )
        self.assertEqual(InscriptionListeAttente.objects.count(), 1)
        self.assertEqual(response.status_code, http.HTTPStatus.FOUND)
        new_inscription = InscriptionListeAttente.objects.last()
        self.assertEqual(new_inscription.ads_manager, self.ads_manager)
        self.assertEqual(new_inscription.numero, inscription.numero)
        self.assertNotEqual(new_inscription.id, inscription.id)

    def test_post_formulaire_creation_inscription_numero_commune(self):
        self.assertEqual(InscriptionListeAttente.objects.count(), 0)
        today = datetime.date.today()
        response = self.client.post(
            reverse(
                "app.liste_attente_inscription",
                kwargs={"manager_id": self.ads_manager.id},
            ),
            data={
                "nom": "John",
                "prenom": "Doe",
                "numero_licence": "1234ABCD",
                "numero_telephone": "0606060606",
                "email": "john.doe@test.com",
                "adresse": "10 Rue du test",
                "date_depot_inscription": today - relativedelta(years=2),
                "date_dernier_renouvellement": today - relativedelta(months=3),
            },
        )
        self.assertEqual(InscriptionListeAttente.objects.count(), 1)
        self.assertEqual(response.status_code, http.HTTPStatus.FOUND)
        inscription = InscriptionListeAttente.objects.last()
        self.assertEqual(inscription.ads_manager, self.ads_manager)
        self.assertIn(
            f"{self.ads_manager.content_object.insee}{inscription.date_depot_inscription.strftime('%d%m%Y')}",
            inscription.numero,
        )

    def test_post_formulaire_creation_inscription_numero_epci(self):
        client, user = self.create_client()
        ads_manager = ADSManagerFactory(for_epci=True)
        ADSManagerRequestFactory(user=user, ads_manager=ads_manager)
        today = datetime.date.today()

        self.assertEqual(InscriptionListeAttente.objects.count(), 0)
        response = client.post(
            reverse(
                "app.liste_attente_inscription",
                kwargs={"manager_id": ads_manager.id},
            ),
            data={
                "nom": "John",
                "prenom": "Doe",
                "numero_licence": "1234ABCD",
                "numero_telephone": "0606060606",
                "email": "john.doe@test.com",
                "adresse": "10 Rue du test",
                "date_depot_inscription": today - relativedelta(years=2),
                "date_dernier_renouvellement": today - relativedelta(months=3),
            },
        )
        self.assertEqual(InscriptionListeAttente.objects.count(), 1)
        self.assertEqual(response.status_code, http.HTTPStatus.FOUND)
        inscription = InscriptionListeAttente.objects.last()
        self.assertEqual(inscription.ads_manager, ads_manager)
        self.assertIn(
            f"{ads_manager.content_object.departement}{inscription.date_depot_inscription.strftime('%d%m%Y')}",
            inscription.numero,
        )

    def test_post_formulaire_creation_inscription_numero_prefecture(self):
        client, user = self.create_client()
        ads_manager = ADSManagerFactory(for_prefecture=True)
        ADSManagerRequestFactory(user=user, ads_manager=ads_manager)
        today = datetime.date.today()

        self.assertEqual(InscriptionListeAttente.objects.count(), 0)
        response = client.post(
            reverse(
                "app.liste_attente_inscription",
                kwargs={"manager_id": ads_manager.id},
            ),
            data={
                "nom": "John",
                "prenom": "Doe",
                "numero_licence": "1234ABCD",
                "numero_telephone": "0606060606",
                "email": "john.doe@test.com",
                "adresse": "10 Rue du test",
                "date_depot_inscription": today - relativedelta(years=2),
                "date_dernier_renouvellement": today - relativedelta(months=3),
            },
        )
        self.assertEqual(InscriptionListeAttente.objects.count(), 1)
        self.assertEqual(response.status_code, http.HTTPStatus.FOUND)
        inscription = InscriptionListeAttente.objects.last()
        self.assertEqual(inscription.ads_manager, ads_manager)
        self.assertIn(
            f"{ads_manager.content_object.numero}{inscription.date_depot_inscription.strftime('%d%m%Y')}",
            inscription.numero,
        )


class TestModificationInscriptionListeAttenteView(ClientTestCase):
    def test_get_formulaire_modification_inscription(self):
        inscription = InscriptionListeAttenteFactory(ads_manager=self.ads_manager)
        self.assertEqual(InscriptionListeAttente.objects.count(), 1)
        response = self.client.get(
            reverse(
                "app.liste_attente_inscription_update",
                kwargs={
                    "manager_id": self.ads_manager.id,
                    "inscription_id": inscription.id,
                },
            ),
        )
        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertIsInstance(response.context["form"], InscriptionListeAttenteForm)
        self.assertEqual(response.context["form"].instance, inscription)
        self.assertTemplateUsed(
            response, "pages/ads_register/liste_attente_inscription.html"
        )

    def test_get_formulaire_modification_inscription_redirection(self):
        ads_manager = ADSManagerFactory(for_commune=True)
        ADSManagerRequestFactory(user=self.user, ads_manager=ads_manager)
        inscription = InscriptionListeAttenteFactory(ads_manager=self.ads_manager)
        self.assertEqual(InscriptionListeAttente.objects.count(), 1)
        response = self.client.get(
            reverse(
                "app.liste_attente_inscription_update",
                kwargs={
                    "manager_id": ads_manager.id,
                    "inscription_id": inscription.id,
                },
            ),
        )
        self.assertRedirects(
            response,
            expected_url=reverse(
                "app.liste_attente_inscription_update",
                kwargs={
                    "manager_id": self.ads_manager.id,
                    "inscription_id": inscription.id,
                },
            ),
            status_code=http.HTTPStatus.FOUND,
            target_status_code=http.HTTPStatus.OK,
            fetch_redirect_response=True,
        )

    def test_post_formulaire_modification_inscription_ok(self):
        inscription = InscriptionListeAttenteFactory(ads_manager=self.ads_manager)
        self.assertEqual(InscriptionListeAttente.objects.count(), 1)
        today = datetime.date.today()
        data = {
            "numero": inscription.numero,
            "nom": "John",
            "prenom": "Doe",
            "numero_licence": "1234ABCD",
            "numero_telephone": "0606060606",
            "email": "john.doe@test.com",
            "adresse": "10 Rue du test",
            "date_depot_inscription": today - relativedelta(years=2),
            "date_dernier_renouvellement": today - relativedelta(months=3),
        }
        response = self.client.post(
            reverse(
                "app.liste_attente_inscription_update",
                kwargs={
                    "manager_id": self.ads_manager.id,
                    "inscription_id": inscription.id,
                },
            ),
            data=data,
        )
        self.assertEqual(response.status_code, http.HTTPStatus.FOUND)
        inscription.refresh_from_db()
        self.assertEqual(inscription.nom, data["nom"])
        self.assertEqual(inscription.prenom, data["prenom"])
        self.assertEqual(inscription.numero_licence, data["numero_licence"])
        self.assertEqual(inscription.numero_telephone, data["numero_telephone"])
        self.assertEqual(inscription.email, data["email"])
        self.assertEqual(inscription.adresse, data["adresse"])
        self.assertEqual(
            inscription.date_depot_inscription, data["date_depot_inscription"]
        )
        self.assertEqual(
            inscription.date_dernier_renouvellement, data["date_dernier_renouvellement"]
        )
        self.assertRedirects(
            response,
            expected_url=reverse(
                "app.liste_attente", kwargs={"manager_id": self.ads_manager.id}
            ),
            status_code=http.HTTPStatus.FOUND,
            target_status_code=http.HTTPStatus.OK,
            fetch_redirect_response=True,
        )

    def test_post_formulaire_modification_inscription_numero_invalide(self):
        inscription = InscriptionListeAttenteFactory(ads_manager=self.ads_manager)
        inscription_2 = InscriptionListeAttenteFactory(ads_manager=self.ads_manager)
        today = datetime.date.today()

        self.assertEqual(InscriptionListeAttente.objects.count(), 2)
        data = {
            "numero": inscription_2.numero,
            "nom": "John",
            "prenom": "Doe",
            "numero_licence": "1234ABCD",
            "numero_telephone": "0606060606",
            "email": "john.doe@test.com",
            "adresse": "10 Rue du test",
            "date_depot_inscription": today - relativedelta(years=2),
            "date_dernier_renouvellement": today - relativedelta(months=3),
        }

        response = self.client.post(
            reverse(
                "app.liste_attente_inscription_update",
                kwargs={
                    "manager_id": self.ads_manager.id,
                    "inscription_id": inscription.id,
                },
            ),
            data=data,
        )
        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertFalse(response.context["form"].is_valid())
        self.assertEqual(
            response.context["form"].errors["numero"],
            [WAITING_LIST_UNIQUE_ERROR_MESSAGE],
        )


class TestFormulaireArchivageView(ClientTestCase):
    def test_get_formulaire_archivage_inscription(self):
        inscription = InscriptionListeAttenteFactory(ads_manager=self.ads_manager)
        self.assertEqual(InscriptionListeAttente.objects.count(), 1)
        response = self.client.get(
            reverse(
                "app.liste_attente_inscription_archivage",
                kwargs={
                    "manager_id": self.ads_manager.id,
                    "inscription_id": inscription.id,
                },
            ),
        )
        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertIsInstance(
            response.context["form"], ArchivageInscriptionListeAttenteForm
        )
        self.assertEqual(response.context["form"].instance, inscription)
        self.assertTemplateUsed(
            response, "pages/ads_register/liste_attente_archivage_inscription.html"
        )

    def test_get_formulaire_archivage_inscription_redirection(self):
        ads_manager = ADSManagerFactory(for_commune=True)
        ADSManagerRequestFactory(user=self.user, ads_manager=ads_manager)
        inscription = InscriptionListeAttenteFactory(ads_manager=self.ads_manager)
        self.assertEqual(InscriptionListeAttente.objects.count(), 1)
        response = self.client.get(
            reverse(
                "app.liste_attente_inscription_archivage",
                kwargs={
                    "manager_id": ads_manager.id,
                    "inscription_id": inscription.id,
                },
            ),
        )
        self.assertRedirects(
            response,
            expected_url=reverse(
                "app.liste_attente_inscription_archivage",
                kwargs={
                    "manager_id": self.ads_manager.id,
                    "inscription_id": inscription.id,
                },
            ),
            status_code=http.HTTPStatus.FOUND,
            target_status_code=http.HTTPStatus.OK,
            fetch_redirect_response=True,
        )

    def test_post_formulaire_archivage_inscription(self):
        inscription = InscriptionListeAttenteFactory(ads_manager=self.ads_manager)
        self.assertEqual(InscriptionListeAttente.objects.count(), 1)
        data = {
            "nom": inscription.nom,
            "prenom": inscription.prenom,
            "numero_licence": inscription.numero_licence,
            "commentaire": "Commentaire",
            "motif_archivage": InscriptionListeAttente.MOTIFS_ARCHIVAGE[0][0],
        }
        response = self.client.post(
            reverse(
                "app.liste_attente_inscription_archivage",
                kwargs={
                    "manager_id": self.ads_manager.id,
                    "inscription_id": inscription.id,
                },
            ),
            data=data,
        )
        self.assertEqual(response.status_code, http.HTTPStatus.FOUND)
        self.assertRedirects(
            response,
            expected_url=reverse(
                "app.liste_attente_inscription_archivage_confirmation",
                kwargs={"manager_id": self.ads_manager.id},
            ),
            status_code=http.HTTPStatus.FOUND,
            target_status_code=http.HTTPStatus.OK,
            fetch_redirect_response=True,
        )
        inscription.refresh_from_db()
        self.assertEqual(InscriptionListeAttente.objects.count(), 0)
        self.assertEqual(InscriptionListeAttente.with_deleted.count(), 1)
        self.assertEqual(inscription.motif_archivage, data["motif_archivage"])


class TestArchivageConfirmationView(ClientTestCase):
    def test_get_archivage_confirmation(self):
        response = self.client.get(
            reverse(
                "app.liste_attente_inscription_archivage_confirmation",
                kwargs={
                    "manager_id": self.ads_manager.id,
                },
            ),
        )
        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertTemplateUsed(
            response,
            "pages/ads_register/liste_attente_archivage_confirmation_inscription.html",
        )


class TestExportListeAttenteView(ClientTestCase):
    def test_get_export_liste_attente(self):
        InscriptionListeAttenteFactory(ads_manager=self.ads_manager)
        InscriptionListeAttenteFactory(ads_manager=self.ads_manager)
        InscriptionListeAttenteFactory(ads_manager=self.ads_manager)

        response = self.client.get(
            reverse(
                "app.liste_attente_export", kwargs={"manager_id": self.ads_manager.id}
            )
        )
        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertEqual(
            response.headers["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


class TestListeAttenteAttributionView(ClientTestCase):
    def test_get_liste_attente_attribution(self):
        today = datetime.date.today()

        # Apparait en premiere car est la plus ancienne
        inscription_1 = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager,
            date_depot_inscription=today - relativedelta(years=2),
            date_dernier_renouvellement=today,
        )

        # Apparait en seconde car la plus récente
        inscription_2 = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager,
            date_depot_inscription=today - relativedelta(years=1),
            date_dernier_renouvellement=today,
        )

        response = self.client.get(
            reverse(
                "app.liste_attente_attribution",
                kwargs={"manager_id": self.ads_manager.id},
            )
        )
        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertTemplateUsed(
            response, "pages/ads_register/liste_attente_attribution.html"
        )
        self.assertListEqual(
            list(response.context["inscriptions"]),
            [inscription_1, inscription_2],
        )


class TestTraitementDemandeView(ClientTestCase):
    def test_get_traitement_demande_view_404(self):
        response = self.client.get(
            reverse(
                "app.liste_attente_traitement_demande",
                kwargs={"manager_id": self.ads_manager.id, "inscription_id": 42},
            )
        )
        self.assertEqual(response.status_code, http.HTTPStatus.NOT_FOUND)

    def test_get_traitement_demande_view_demande_archivee(self):
        today = datetime.date.today()
        inscription = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager,
            date_depot_inscription=today - relativedelta(years=1),
            date_dernier_renouvellement=today,
            status=InscriptionListeAttente.INSCRIT,
        )
        inscription.delete()
        response = self.client.get(
            reverse(
                "app.liste_attente_traitement_demande",
                kwargs={
                    "manager_id": self.ads_manager.id,
                    "inscription_id": inscription.id,
                },
            )
        )
        self.assertEqual(response.status_code, http.HTTPStatus.NOT_FOUND)

    def test_get_traitement_demande_view_etape_1(self):
        today = datetime.date.today()
        inscription = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager,
            date_depot_inscription=today - relativedelta(years=1),
            date_dernier_renouvellement=today,
            status=InscriptionListeAttente.INSCRIT,
        )
        response = self.client.get(
            reverse(
                "app.liste_attente_traitement_demande",
                kwargs={
                    "manager_id": self.ads_manager.id,
                    "inscription_id": inscription.id,
                },
            )
        )
        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertTemplateUsed(
            "pages/ads_register/liste_attente_traitement_demande.html"
        )
        self.assertTemplateUsed(
            "pages/ads_register/liste_attente_attribution_etape_1.html"
        )
        self.assertTemplateNotUsed(
            "pages/ads_register/liste_attente_attribution_etape_2.html"
        )
        self.assertTemplateNotUsed(
            "pages/ads_register/liste_attente_attribution_etape_3.html"
        )
        self.assertIsInstance(
            response.context["form"], ContactInscriptionListeAttenteForm
        )
        self.assertEqual(response.context["inscription"], inscription)

    def test_post_traitement_demande_view_etape_1_ok(self):
        today = datetime.date.today()
        inscription = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager,
            date_depot_inscription=today - relativedelta(years=1),
            date_dernier_renouvellement=today,
            status=InscriptionListeAttente.INSCRIT,
        )
        data = {
            "date_contact": today,
            "delai_reponse": 15,
            "action": "contact",
        }
        response = self.client.post(
            reverse(
                "app.liste_attente_traitement_demande",
                kwargs={
                    "manager_id": self.ads_manager.id,
                    "inscription_id": inscription.id,
                },
            ),
            data,
        )
        self.assertRedirects(
            response,
            expected_url=reverse(
                "app.liste_attente_traitement_demande",
                kwargs={
                    "manager_id": self.ads_manager.id,
                    "inscription_id": inscription.id,
                },
            ),
            status_code=http.HTTPStatus.FOUND,
            target_status_code=http.HTTPStatus.OK,
            fetch_redirect_response=True,
        )
        inscription.refresh_from_db()
        self.assertEqual(inscription.date_contact, data["date_contact"])
        self.assertEqual(inscription.delai_reponse, data["delai_reponse"])
        self.assertEqual(inscription.status, InscriptionListeAttente.ATTENTE_REPONSE)

    def test_post_traitement_demande_view_etape_1_empty_form(self):
        today = datetime.date.today()
        inscription = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager,
            date_depot_inscription=today - relativedelta(years=1),
            date_dernier_renouvellement=today,
            status=InscriptionListeAttente.INSCRIT,
        )
        data = {
            "date_contact": "",
            "delai_reponse": "",
            "action": "contact",
        }
        response = self.client.post(
            reverse(
                "app.liste_attente_traitement_demande",
                kwargs={
                    "manager_id": self.ads_manager.id,
                    "inscription_id": inscription.id,
                },
            ),
            data,
        )
        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertEqual(
            response.context["form"].errors,
            {
                "date_contact": [ContactInscriptionListeAttenteForm.EMPTY_DATE_CONTACT],
                "delai_reponse": [
                    ContactInscriptionListeAttenteForm.EMPTY_DELAI_REPONSE
                ],
            },
        )
        inscription.refresh_from_db()
        self.assertEqual(inscription.status, InscriptionListeAttente.INSCRIT)

    def test_get_traitement_demande_view_etape_2(self):
        today = datetime.date.today()
        inscription = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager,
            date_depot_inscription=today - relativedelta(years=1),
            date_dernier_renouvellement=today,
            date_contact=today,
            delai_reponse=15,
            status=InscriptionListeAttente.ATTENTE_REPONSE,
        )
        response = self.client.get(
            reverse(
                "app.liste_attente_traitement_demande",
                kwargs={
                    "manager_id": self.ads_manager.id,
                    "inscription_id": inscription.id,
                },
            )
        )
        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertTemplateUsed(
            "pages/ads_register/liste_attente_traitement_demande.html"
        )
        self.assertTemplateNotUsed(
            "pages/ads_register/liste_attente_attribution_etape_1.html"
        )
        self.assertTemplateUsed(
            "pages/ads_register/liste_attente_attribution_etape_2.html"
        )
        self.assertTemplateNotUsed(
            "pages/ads_register/liste_attente_attribution_etape_3.html"
        )
        self.assertIsInstance(
            response.context["form"], UpdateDelaiInscriptionListeAttenteForm
        )
        self.assertEqual(response.context["inscription"], inscription)

    def test_post_traitement_demande_view_etape_2_update_delai(self):
        today = datetime.date.today()
        inscription = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager,
            date_depot_inscription=today - relativedelta(years=1),
            date_dernier_renouvellement=today,
            date_contact=today,
            delai_reponse=15,
            status=InscriptionListeAttente.ATTENTE_REPONSE,
        )
        data = {
            "delai_reponse": 10,
            "action": "update_delai",
        }
        response = self.client.post(
            reverse(
                "app.liste_attente_traitement_demande",
                kwargs={
                    "manager_id": self.ads_manager.id,
                    "inscription_id": inscription.id,
                },
            ),
            data,
        )
        self.assertRedirects(
            response,
            expected_url=reverse(
                "app.liste_attente_traitement_demande",
                kwargs={
                    "manager_id": self.ads_manager.id,
                    "inscription_id": inscription.id,
                },
            ),
            status_code=http.HTTPStatus.FOUND,
            target_status_code=http.HTTPStatus.OK,
            fetch_redirect_response=True,
        )
        inscription.refresh_from_db()
        self.assertEqual(inscription.delai_reponse, data["delai_reponse"])
        self.assertEqual(inscription.status, InscriptionListeAttente.ATTENTE_REPONSE)

    def test_post_traitement_demande_view_etape_2_update_delai_empty(self):
        today = datetime.date.today()
        inscription = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager,
            date_depot_inscription=today - relativedelta(years=1),
            date_dernier_renouvellement=today,
            date_contact=today,
            delai_reponse=15,
            status=InscriptionListeAttente.ATTENTE_REPONSE,
        )
        data = {
            "delai_reponse": "",
            "action": "update_delai",
        }
        response = self.client.post(
            reverse(
                "app.liste_attente_traitement_demande",
                kwargs={
                    "manager_id": self.ads_manager.id,
                    "inscription_id": inscription.id,
                },
            ),
            data,
        )
        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertEqual(
            response.context["form"].errors,
            {
                "delai_reponse": [
                    UpdateDelaiInscriptionListeAttenteForm.EMPTY_DELAI_REPONSE
                ],
            },
        )
        inscription.refresh_from_db()
        self.assertEqual(inscription.delai_reponse, 15)
        self.assertEqual(inscription.status, InscriptionListeAttente.ATTENTE_REPONSE)

    def test_post_traitement_demande_view_etape_2_validation_reponse(self):
        today = datetime.date.today()
        inscription = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager,
            date_depot_inscription=today - relativedelta(years=1),
            date_dernier_renouvellement=today,
            date_contact=today,
            delai_reponse=15,
            status=InscriptionListeAttente.ATTENTE_REPONSE,
        )
        data = {
            "action": "validation_reponse",
        }
        response = self.client.post(
            reverse(
                "app.liste_attente_traitement_demande",
                kwargs={
                    "manager_id": self.ads_manager.id,
                    "inscription_id": inscription.id,
                },
            ),
            data,
        )
        self.assertRedirects(
            response,
            expected_url=reverse(
                "app.liste_attente_traitement_demande",
                kwargs={
                    "manager_id": self.ads_manager.id,
                    "inscription_id": inscription.id,
                },
            ),
            status_code=http.HTTPStatus.FOUND,
            target_status_code=http.HTTPStatus.OK,
            fetch_redirect_response=True,
        )
        inscription.refresh_from_db()
        self.assertEqual(inscription.status, InscriptionListeAttente.REPONSE_OK)

    def test_post_traitement_demande_view_etape_2_reset_demande(self):
        today = datetime.date.today()
        inscription = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager,
            date_depot_inscription=today - relativedelta(years=1),
            date_dernier_renouvellement=today,
            date_contact=today,
            delai_reponse=15,
            status=InscriptionListeAttente.ATTENTE_REPONSE,
        )
        data = {
            "action": "reset_demande",
        }
        response = self.client.post(
            reverse(
                "app.liste_attente_traitement_demande",
                kwargs={
                    "manager_id": self.ads_manager.id,
                    "inscription_id": inscription.id,
                },
            ),
            data,
        )
        self.assertRedirects(
            response,
            expected_url=reverse(
                "app.liste_attente",
                kwargs={
                    "manager_id": self.ads_manager.id,
                },
            ),
            status_code=http.HTTPStatus.FOUND,
            target_status_code=http.HTTPStatus.OK,
            fetch_redirect_response=True,
        )
        inscription.refresh_from_db()
        self.assertEqual(inscription.status, InscriptionListeAttente.INSCRIT)
        self.assertIsNone(inscription.date_contact)
        self.assertIsNone(inscription.delai_reponse)

    def test_get_traitement_demande_view_etape_3(self):
        today = datetime.date.today()
        inscription = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager,
            date_depot_inscription=today - relativedelta(years=1),
            date_dernier_renouvellement=today,
            date_contact=today,
            delai_reponse=15,
            status=InscriptionListeAttente.REPONSE_OK,
        )
        response = self.client.get(
            reverse(
                "app.liste_attente_traitement_demande",
                kwargs={
                    "manager_id": self.ads_manager.id,
                    "inscription_id": inscription.id,
                },
            )
        )
        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertTemplateUsed(
            "pages/ads_register/liste_attente_traitement_demande.html"
        )
        self.assertTemplateNotUsed(
            "pages/ads_register/liste_attente_attribution_etape_1.html"
        )
        self.assertTemplateNotUsed(
            "pages/ads_register/liste_attente_attribution_etape_2.html"
        )
        self.assertTemplateUsed(
            "pages/ads_register/liste_attente_attribution_etape_3.html"
        )
        self.assertEqual(response.context["inscription"], inscription)

    def test_post_traitement_demande_view_etape_3_empty(self):
        today = datetime.date.today()
        inscription = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager,
            date_depot_inscription=today - relativedelta(years=1),
            date_dernier_renouvellement=today,
            date_contact=today,
            delai_reponse=15,
            status=InscriptionListeAttente.REPONSE_OK,
        )
        self.assertEqual(ADS.objects.count(), 0)

        response = self.client.post(
            reverse(
                "app.liste_attente_traitement_demande",
                kwargs={
                    "manager_id": self.ads_manager.id,
                    "inscription_id": inscription.id,
                },
            ),
            data={"action": "attribution_ads"},
        )
        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertEqual(
            response.context["form"].errors,
            {
                "numero": ["Ce champ est obligatoire."],
                "date_attribution": ["Ce champ est obligatoire."],
                "arrete": ["Ce champ est obligatoire."],
            },
        )
        self.assertEqual(ADS.objects.count(), 0)

    def test_post_traitement_demande_view_etape_3_used_number(self):
        today = datetime.date.today()
        inscription = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager,
            date_depot_inscription=today - relativedelta(years=1),
            date_dernier_renouvellement=today,
            date_contact=today,
            delai_reponse=15,
            status=InscriptionListeAttente.REPONSE_OK,
        )
        ads = ADSFactory(ads_manager=self.ads_manager)
        self.assertEqual(ADS.objects.count(), 1)

        response = self.client.post(
            reverse(
                "app.liste_attente_traitement_demande",
                kwargs={
                    "manager_id": self.ads_manager.id,
                    "inscription_id": inscription.id,
                },
            ),
            data={
                "action": "attribution_ads",
                "numero": ads.number,
                "date_attribution": today,
                "arrete": SimpleUploadedFile(
                    "arrete.pdf", b"Contenu arrete", content_type="application/pdf"
                ),
            },
        )
        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertEqual(
            response.context["form"].errors,
            {
                "numero": ["Ce numéro est déjà utilisé par une autre ADS."],
            },
        )
        self.assertEqual(ADS.objects.count(), 1)

    def test_post_traitement_demande_view_etape_3_ok(self):
        today = datetime.date.today()
        inscription = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager,
            date_depot_inscription=today - relativedelta(years=1),
            date_dernier_renouvellement=today,
            date_contact=today,
            delai_reponse=15,
            status=InscriptionListeAttente.REPONSE_OK,
        )
        self.assertEqual(ADS.objects.count(), 0)
        self.assertEqual(ADSUser.objects.count(), 0)
        self.assertEqual(ADSLegalFile.objects.count(), 0)
        self.assertEqual(ADSUpdateLog.objects.count(), 0)

        response = self.client.post(
            reverse(
                "app.liste_attente_traitement_demande",
                kwargs={
                    "manager_id": self.ads_manager.id,
                    "inscription_id": inscription.id,
                },
            ),
            data={
                "action": "attribution_ads",
                "numero": "1",
                "date_attribution": today,
                "arrete": SimpleUploadedFile(
                    "arrete.pdf", b"Contenu arrete", content_type="application/pdf"
                ),
            },
        )
        self.assertEqual(ADS.objects.count(), 1)
        ads = ADS.objects.last()
        self.assertEqual(ads.ads_manager, inscription.ads_manager)
        self.assertEqual(ads.number, "1")
        self.assertEqual(ads.ads_creation_date, today)
        self.assertEqual(ads.owner_name, f"{inscription.nom} {inscription.prenom}")
        self.assertEqual(ads.owner_phone, inscription.numero_telephone)
        self.assertEqual(ads.owner_email, inscription.email)

        self.assertEqual(
            ADSUser.objects.filter(
                ads=ads,
                status=ADSUser.TITULAIRE_EXPLOITANT,
                license_number=inscription.numero_licence,
            ).count(),
            1,
        )
        self.assertEqual(ADSLegalFile.objects.filter(ads=ads).count(), 1)
        self.assertEqual(ADSUpdateLog.objects.filter(ads=ads).count(), 1)

        self.assertRedirects(
            response,
            expected_url=reverse(
                "app.ads.detail",
                kwargs={"manager_id": inscription.ads_manager.id, "ads_id": ads.id},
            ),
            status_code=http.HTTPStatus.FOUND,
            target_status_code=http.HTTPStatus.OK,
            fetch_redirect_response=True,
        )


class TestListesAttentePubliquesView(ClientTestCase):
    def test_get_listes_attente_publique(self):
        self.ads_manager.liste_attente_publique = True
        self.ads_manager.save()
        response = self.client.get(reverse("app.listes_attentes"))

        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertTemplateUsed("pages/ads_register/listes_attentes_publiques.html")
        self.assertEqual(0, response.context["ads_managers"].count())

    def test_get_listes_attente_publique_search_by_departement(self):
        self.ads_manager.liste_attente_publique = True
        self.ads_manager.save()
        response = self.client.get(
            reverse("app.listes_attentes")
            + f"?departement={self.ads_manager.administrator.prefecture.id}"
        )

        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertTemplateUsed("pages/ads_register/listes_attentes_publiques.html")
        self.assertIn(self.ads_manager, response.context["ads_managers"])

    def test_get_listes_attente_publique_search_by_libelle(self):
        self.ads_manager.liste_attente_publique = True
        self.ads_manager.save()
        response = self.client.get(
            reverse("app.listes_attentes")
            + f"?commune={self.ads_manager.content_object.libelle}"
        )

        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertTemplateUsed("pages/ads_register/listes_attentes_publiques.html")
        self.assertIn(self.ads_manager, response.context["ads_managers"])

    def test_get_listes_attente_publique_search_by_libelle_not_public(self):
        response = self.client.get(
            reverse("app.listes_attentes")
            + f"?commune={self.ads_manager.content_object.libelle}"
        )

        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertTemplateUsed("pages/ads_register/listes_attentes_publiques.html")
        self.assertNotIn(self.ads_manager, response.context["ads_managers"])


class TestListeAttentePubliqueView(ClientTestCase):
    def test_get_liste_attente_privee(self):
        response = self.client.get(
            reverse(
                "app.liste_attente_publique", kwargs={"manager_id": self.ads_manager.id}
            )
        )

        self.assertEqual(response.status_code, http.HTTPStatus.NOT_FOUND)

    def test_get_liste_attente_publique(self):
        self.ads_manager.liste_attente_publique = True
        self.ads_manager.save()
        response = self.client.get(
            reverse(
                "app.liste_attente_publique", kwargs={"manager_id": self.ads_manager.id}
            )
        )

        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertTemplateUsed("pages/ads_register/liste_attente_publique.html")


class ChangeListeAttentePublicView(ClientTestCase):
    def test_change_liste_publique(self):
        response = self.client.post(
            reverse(
                "app.liste_attente_make_public",
                kwargs={"manager_id": self.ads_manager.id},
            ),
            data={"liste_attente_publique": ["0", "1"]},
        )

        self.assertRedirects(
            response,
            expected_url=reverse(
                "app.liste_attente",
                kwargs={
                    "manager_id": self.ads_manager.id,
                },
            ),
            status_code=http.HTTPStatus.FOUND,
            target_status_code=http.HTTPStatus.OK,
            fetch_redirect_response=True,
        )
        self.ads_manager.refresh_from_db()
        self.assertTrue(self.ads_manager.liste_attente_publique)

    def test_change_liste_privee(self):
        self.ads_manager.liste_attente_publique = True
        self.ads_manager.save()

        response = self.client.post(
            reverse(
                "app.liste_attente_make_public",
                kwargs={"manager_id": self.ads_manager.id},
            ),
            data={"liste_attente_publique": "0"},
        )

        self.assertRedirects(
            response,
            expected_url=reverse(
                "app.liste_attente",
                kwargs={
                    "manager_id": self.ads_manager.id,
                },
            ),
            status_code=http.HTTPStatus.FOUND,
            target_status_code=http.HTTPStatus.OK,
            fetch_redirect_response=True,
        )
        self.ads_manager.refresh_from_db()
        self.assertFalse(self.ads_manager.liste_attente_publique)
