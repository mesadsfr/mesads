import logging
import datetime
import http
from django.urls import reverse

from mesads.app.models import InscriptionListeAttente, WAITING_LIST_UNIQUE_ERROR_MESSAGE
from mesads.users.unittest import ClientTestCase
from mesads.app.forms import (
    InscriptionListeAttenteForm,
    ArchivageInscriptionListeAttenteForm,
)

from ..factories import (
    ADSManagerRequestFactory,
    ADSManagerFactory,
    InscriptionListeAttenteFactory,
)


class TestADSManagerAdminRequestsView(ClientTestCase):
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
        assert inscription in response.context["inscriptions"]
        assert other_inscription not in response.context["inscriptions"]
        assert inscription_archived not in response.context["inscriptions"]
        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertTemplateUsed(response, "pages/ads_register/liste_attente.html")

    def test_get_liste_attente_search(self):
        inscription_1 = InscriptionListeAttenteFactory(ads_manager=self.ads_manager)
        inscription_2 = InscriptionListeAttenteFactory(ads_manager=self.ads_manager)
        inscription_3 = InscriptionListeAttenteFactory(ads_manager=self.ads_manager)

        response = self.client.get(
            f"{reverse('app.liste_attente', kwargs={'manager_id': self.ads_manager.id})}?search={inscription_1.nom}+{inscription_1.prenom}"
        )
        assert inscription_1 in response.context["inscriptions"]
        assert inscription_2 not in response.context["inscriptions"]
        assert inscription_3 not in response.context["inscriptions"]
        self.assertEqual(response.status_code, http.HTTPStatus.OK)

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
        assert inscription_archived in response.context["inscriptions"]
        assert other_inscription not in response.context["inscriptions"]
        assert other_inscription_archived not in response.context["inscriptions"]
        assert inscription not in response.context["inscriptions"]
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
        assert inscription_archived in response.context["inscriptions"]
        assert other_inscription_archived not in response.context["inscriptions"]
        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertTemplateUsed(
            response, "pages/ads_register/liste_attente_archivees.html"
        )

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
        assert InscriptionListeAttente.objects.count() == 0
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
                "date_depot_inscription": datetime.date.today(),
                "date_dernier_renouvellement": datetime.date.today(),
                "date_fin_validite": datetime.date.today()
                + datetime.timedelta(days=365),
            },
        )
        assert InscriptionListeAttente.objects.count() == 1
        self.assertEqual(response.status_code, http.HTTPStatus.FOUND)
        inscription = InscriptionListeAttente.objects.last()
        assert inscription.ads_manager == self.ads_manager

    def test_post_formulaire_creation_inscription_numero_invalide(self):
        inscription = InscriptionListeAttenteFactory(ads_manager=self.ads_manager)
        assert InscriptionListeAttente.objects.count() == 1
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
        assert InscriptionListeAttente.objects.count() == 1
        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        assert not response.context["form"].is_valid()
        assert response.context["form"].errors["numero"] == [
            WAITING_LIST_UNIQUE_ERROR_MESSAGE
        ]

    def test_post_formulaire_creation_inscription_numero_valide(self):
        inscription = InscriptionListeAttenteFactory(ads_manager=self.ads_manager)
        inscription.delete()
        assert InscriptionListeAttente.objects.count() == 0
        assert InscriptionListeAttente.with_deleted.count() == 1
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
        assert InscriptionListeAttente.objects.count() == 1
        self.assertEqual(response.status_code, http.HTTPStatus.FOUND)
        new_inscription = InscriptionListeAttente.objects.last()
        assert new_inscription.ads_manager == self.ads_manager
        assert new_inscription.numero == inscription.numero
        assert new_inscription.id != inscription.id

    def test_post_formulaire_creation_inscription_dates_invalides(self):
        assert InscriptionListeAttente.objects.count() == 0
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
                "date_depot_inscription": datetime.date.today()
                - datetime.timedelta(days=365),
                "date_dernier_renouvellement": datetime.date.today()
                - datetime.timedelta(days=365),
                "date_fin_validite": datetime.date.today() - datetime.timedelta(days=1),
            },
        )
        assert InscriptionListeAttente.objects.count() == 0
        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        assert not response.context["form"].is_valid()
        assert response.context["form"].errors["date_dernier_renouvellement"] == [
            InscriptionListeAttenteForm.ERROR_DATE_RENOUVELLEMENT
        ]
        assert response.context["form"].errors["date_fin_validite"] == [
            InscriptionListeAttenteForm.ERROR_DATE_FIN_VALIDITE
        ]

    def test_get_formulaire_modification_inscription(self):
        inscription = InscriptionListeAttenteFactory(ads_manager=self.ads_manager)
        assert InscriptionListeAttente.objects.count() == 1
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
        assert isinstance(response.context["form"], InscriptionListeAttenteForm)
        assert response.context["form"].instance == inscription
        self.assertTemplateUsed(
            response, "pages/ads_register/inscription_liste_attente.html"
        )

    def test_get_formulaire_modification_inscription_redirection(self):
        ads_manager = ADSManagerFactory(for_commune=True)
        ADSManagerRequestFactory(user=self.user, ads_manager=ads_manager)
        inscription = InscriptionListeAttenteFactory(ads_manager=self.ads_manager)
        assert InscriptionListeAttente.objects.count() == 1
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
        assert InscriptionListeAttente.objects.count() == 1
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
        assert inscription.nom == data["nom"]
        assert inscription.prenom == data["prenom"]
        assert inscription.numero_licence == data["numero_licence"]
        assert inscription.numero_telephone == data["numero_telephone"]
        assert inscription.email == data["email"]
        assert inscription.adresse == data["adresse"]
        assert inscription.date_depot_inscription == data["date_depot_inscription"]
        assert (
            inscription.date_dernier_renouvellement
            == data["date_dernier_renouvellement"]
        )
        assert inscription.date_fin_validite == data["date_fin_validite"]
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
        assert InscriptionListeAttente.objects.count() == 2
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
        assert not response.context["form"].is_valid()
        assert response.context["form"].errors["numero"] == [
            WAITING_LIST_UNIQUE_ERROR_MESSAGE
        ]

    def test_get_formulaire_archivage_inscription(self):
        inscription = InscriptionListeAttenteFactory(ads_manager=self.ads_manager)
        assert InscriptionListeAttente.objects.count() == 1
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
        assert isinstance(
            response.context["form"], ArchivageInscriptionListeAttenteForm
        )
        assert response.context["form"].instance == inscription
        self.assertTemplateUsed(
            response, "pages/ads_register/archivage_inscription_liste_attente.html"
        )

    def test_get_formulaire_archivage_inscription_redirection(self):
        ads_manager = ADSManagerFactory(for_commune=True)
        ADSManagerRequestFactory(user=self.user, ads_manager=ads_manager)
        inscription = InscriptionListeAttenteFactory(ads_manager=self.ads_manager)
        assert InscriptionListeAttente.objects.count() == 1
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
        assert InscriptionListeAttente.objects.count() == 1
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
        assert inscription.motif_archivage == data["motif_archivage"]
        assert InscriptionListeAttente.objects.count() == 0
        assert InscriptionListeAttente.with_deleted.count() == 1

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
        assert (
            response.headers["Content-Type"]
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
