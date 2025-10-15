import logging
import datetime
import http
from dateutil.relativedelta import relativedelta
from django.urls import reverse

from mesads.app.models import (
    InscriptionListeAttente,
    WAITING_LIST_UNIQUE_ERROR_MESSAGE,
    ADS,
    ADSUser,
)
from mesads.users.unittest import ClientTestCase as BaseClientTestCase
from mesads.app.forms import (
    InscriptionListeAttenteForm,
    ArchivageInscriptionListeAttenteForm,
    ContactInscriptionListeAttenteForm,
    UpdateDelaiInscriptionListeAttenteForm,
)

from ..factories import (
    ADSManagerRequestFactory,
    ADSManagerFactory,
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

        response = self.client.get(
            f"{reverse('app.liste_attente', kwargs={'manager_id': self.ads_manager.id})}?search={inscription_1.nom}+{inscription_1.prenom}"
        )
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

        response = self.client.get(
            f"{reverse('app.liste_attente_archives', kwargs={'manager_id': self.ads_manager.id})}?search={inscription_archived.nom}+{inscription_archived.prenom}"
        )
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
            response, "pages/ads_register/inscription_liste_attente.html"
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

    def test_post_formulaire_creation_inscription_with_expired_date_renouvellement(
        self,
    ):
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
                "date_depot_inscription": today - relativedelta(years=3),
                "date_dernier_renouvellement": today - relativedelta(years=2),
            },
        )
        self.assertEqual(InscriptionListeAttente.objects.count(), 0)
        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertEqual(
            response.context["form"].errors["date_dernier_renouvellement"],
            [InscriptionListeAttenteForm.ERROR_DATE_RENOUVELLEMENT],
        )

    def test_post_formulaire_creation_inscription_numero_invalide(self):
        inscription = InscriptionListeAttenteFactory(ads_manager=self.ads_manager)
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
                "date_depot_inscription": datetime.date.today(),
                "date_dernier_renouvellement": datetime.date.today(),
                "date_fin_validite": datetime.date.today()
                + datetime.timedelta(days=365),
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
                "date_depot_inscription": datetime.date.today(),
                "date_dernier_renouvellement": datetime.date.today(),
                "date_fin_validite": datetime.date.today()
                + datetime.timedelta(days=365),
            },
        )
        self.assertEqual(InscriptionListeAttente.objects.count(), 1)
        self.assertEqual(response.status_code, http.HTTPStatus.FOUND)
        new_inscription = InscriptionListeAttente.objects.last()
        self.assertEqual(new_inscription.ads_manager, self.ads_manager)
        self.assertEqual(new_inscription.numero, inscription.numero)
        self.assertNotEqual(new_inscription.id, inscription.id)


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
            response, "pages/ads_register/inscription_liste_attente.html"
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
        data = {
            "numero": inscription.numero,
            "nom": "John",
            "prenom": "Doe",
            "numero_licence": "1234ABCD",
            "numero_telephone": "0606060606",
            "email": "john.doe@test.com",
            "adresse": "10 Rue du test",
            "date_depot_inscription": datetime.date.today(),
            "date_dernier_renouvellement": datetime.date.today(),
            "date_fin_validite": datetime.date.today() + datetime.timedelta(days=365),
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
        self.assertEqual(inscription.date_fin_validite, data["date_fin_validite"])
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
        self.assertEqual(InscriptionListeAttente.objects.count(), 2)
        data = {
            "numero": inscription_2.numero,
            "nom": "John",
            "prenom": "Doe",
            "numero_licence": "1234ABCD",
            "numero_telephone": "0606060606",
            "email": "john.doe@test.com",
            "adresse": "10 Rue du test",
            "date_depot_inscription": datetime.date.today(),
            "date_dernier_renouvellement": datetime.date.today(),
            "date_fin_validite": datetime.date.today() + datetime.timedelta(days=365),
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
            response, "pages/ads_register/archivage_inscription_liste_attente.html"
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
            "pages/ads_register/archivage_confirmation_inscription_liste_attente.html",
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

        # Inscription expiré => Ne devrait pas apparaitre
        inscription_1 = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager,
            date_depot_inscription=today - relativedelta(years=2),
            date_dernier_renouvellement=None,
        )

        # Inscription valide: doit apparaitre en seconde
        # Car exploitation ADS = False
        inscription_2 = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager,
            date_depot_inscription=today - relativedelta(years=2),
            date_dernier_renouvellement=today,
            exploitation_ads=False,
        )

        # Inscription valide: doit apparaitre en premier
        inscription_3 = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager,
            date_depot_inscription=today - relativedelta(years=1),
            date_dernier_renouvellement=today,
            exploitation_ads=True,
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
        self.assertNotIn(inscription_1, response.context["inscriptions"])
        self.assertListEqual(
            list(response.context["inscriptions"]), [inscription_3, inscription_2]
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
            exploitation_ads=True,
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
            exploitation_ads=True,
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
            exploitation_ads=True,
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
            exploitation_ads=True,
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
            exploitation_ads=True,
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
            exploitation_ads=True,
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
            exploitation_ads=True,
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
            exploitation_ads=True,
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

    def test_get_traitement_demande_view_etape_3(self):
        today = datetime.date.today()
        inscription = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager,
            date_depot_inscription=today - relativedelta(years=1),
            date_dernier_renouvellement=today,
            exploitation_ads=True,
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


class TestCreationADSDepuisListeAttente(ClientTestCase):
    def test_get_ads_creation_404(self):
        response = self.client.get(
            f"{reverse('app.ads.create', kwargs={'manager_id': self.ads_manager.id})}?inscription_id=42"
        )
        self.assertEqual(response.status_code, http.HTTPStatus.NOT_FOUND)

    def test_get_ads_creation_demande_archivee(self):
        today = datetime.date.today()
        inscription = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager,
            date_depot_inscription=today - relativedelta(years=1),
            date_dernier_renouvellement=today,
            exploitation_ads=True,
            date_contact=today,
            delai_reponse=15,
            status=InscriptionListeAttente.REPONSE_OK,
        )
        inscription.delete()
        response = self.client.get(
            f"{reverse('app.ads.create', kwargs={'manager_id': self.ads_manager.id})}?inscription_id={inscription.id}"
        )
        self.assertEqual(response.status_code, http.HTTPStatus.NOT_FOUND)

    def test_get_ads_creation_ok(self):
        today = datetime.date.today()
        inscription = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager,
            date_depot_inscription=today - relativedelta(years=1),
            date_dernier_renouvellement=today,
            exploitation_ads=True,
            date_contact=today,
            delai_reponse=15,
            status=InscriptionListeAttente.REPONSE_OK,
        )
        response = self.client.get(
            f"{reverse('app.ads.create', kwargs={'manager_id': self.ads_manager.id})}?inscription_id={inscription.id}"
        )
        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertEqual(
            response.context["form"].initial,
            {
                "ads_creation_date": today,
                "ads_in_use": True,
                "owner_name": f"{inscription.nom} {inscription.prenom}",
                "owner_phone": inscription.numero_telephone,
                "owner_email": inscription.email,
            },
        )
        self.assertEqual(
            response.context["ads_users_formset"].initial_extra,
            [{"license_number": inscription.numero_licence}],
        )

    def test_post_ads_creation_ok(self):
        today = datetime.date.today()
        inscription = InscriptionListeAttenteFactory(
            ads_manager=self.ads_manager,
            date_depot_inscription=today - relativedelta(years=1),
            date_dernier_renouvellement=today,
            exploitation_ads=True,
            date_contact=today,
            delai_reponse=15,
            status=InscriptionListeAttente.REPONSE_OK,
        )
        self.assertEqual(ADS.objects.count(), 0)
        self.assertEqual(ADSUser.objects.count(), 0)
        self.assertIsNone(inscription.deleted_at)
        data = {
            "number": "1",
            "ads_creation_date": today,
            "ads_in_use": True,
            "owner_name": f"{inscription.nom} {inscription.prenom}",
            "owner_phone": inscription.numero_telephone,
            "owner_email": inscription.email,
            "adslegalfile_set-INITIAL_FORMS": ["0"],
            "adslegalfile_set-MAX_NUM_FORMS": ["1000"],
            "adslegalfile_set-MIN_NUM_FORMS": ["0"],
            "adslegalfile_set-TOTAL_FORMS": ["0"],
            "adsuser_set-0-ads": [""],
            "adsuser_set-0-id": [""],
            "adsuser_set-0-license_number": [inscription.numero_licence],
            "adsuser_set-0-status": ["titulaire_exploitant"],
            "adsuser_set-INITIAL_FORMS": ["0"],
            "adsuser_set-MAX_NUM_FORMS": ["1000"],
            "adsuser_set-MIN_NUM_FORMS": ["0"],
            "adsuser_set-TOTAL_FORMS": ["1"],
            "certify": ["on"],
        }
        response = self.client.post(
            f"{reverse('app.ads.create', kwargs={'manager_id': self.ads_manager.id})}?inscription_id={inscription.id}",
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
        self.assertEqual(ADS.objects.count(), 1)
        ads = ADS.objects.last()
        self.assertEqual(ads.ads_manager, inscription.ads_manager)
        self.assertEqual(ads.owner_name, f"{inscription.nom} {inscription.prenom}")
        self.assertEqual(ads.owner_phone, inscription.numero_telephone)
        self.assertEqual(ads.owner_email, inscription.email)
        self.assertEqual(ADSUser.objects.count(), 1)
        ads_user = ADSUser.objects.first()
        self.assertEqual(ads_user.ads, ads)
        self.assertEqual(ads_user.status, ADSUser.TITULAIRE_EXPLOITANT)
        self.assertEqual(ads_user.license_number, inscription.numero_licence)
        inscription.refresh_from_db()
        self.assertIsNotNone(inscription.deleted_at)
        self.assertEqual(
            inscription.motif_archivage, InscriptionListeAttente.ADS_ATTRIBUEE
        )
