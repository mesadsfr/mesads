from .unittest import ClientTestCase

from mesads.fradm.models import Prefecture

from mesads.vehicules_relais.models import Proprietaire, Vehicule


class TestIndexView(ClientTestCase):
    def test_200(self):
        resp = self.anonymous_client.get("/registre_vehicules_relais/")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            resp.headers["Location"], "/registre_vehicules_relais/consulter"
        )


class TestSearchView(ClientTestCase):
    def test_get(self):
        resp = self.anonymous_client.get("/registre_vehicules_relais/consulter")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context["is_proprietaire"])

        resp = self.proprietaire_client.get("/registre_vehicules_relais/consulter")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["is_proprietaire"])

    def test_post(self):
        prefecture = Prefecture.objects.filter(numero="35").get()

        for client in (self.anonymous_client, self.proprietaire_client):
            resp = client.post(
                "/registre_vehicules_relais/consulter",
                {
                    "prefecture": prefecture.id,
                },
            )
            self.assertEqual(resp.status_code, 302)
            self.assertEqual(
                resp.headers["Location"],
                "/registre_vehicules_relais/consulter/departements/35",
            )


class TestSearchDepartementView(ClientTestCase):
    def test_get(self):
        for client in self.anonymous_client, self.proprietaire_client:
            resp = client.get("/registre_vehicules_relais/consulter/departements/35")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.context["prefecture"].numero, "35")
            self.assertEqual(resp.context["object_list"].count(), 4)

            resp = client.get("/registre_vehicules_relais/consulter/departements/33")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.context["prefecture"].numero, "33")
            self.assertEqual(resp.context["object_list"].count(), 1)


class TestVehiculeView(ClientTestCase):
    def test_get(self):
        vehicule = Vehicule.objects.first()
        for client in self.anonymous_client, self.proprietaire_client:
            resp = client.get(
                f"/registre_vehicules_relais/consulter/vehicules/{vehicule.numero}"
            )
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.context["vehicule"], vehicule)

            resp = client.get("/registre_vehicules_relais/consulter/vehicules/33-999")
            self.assertEqual(resp.status_code, 404)


class TestProprietaireListView(ClientTestCase):
    def test_get(self):
        resp = self.anonymous_client.get("/registre_vehicules_relais/proprietaire")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            resp.headers["Location"],
            "/auth/login/?next=/registre_vehicules_relais/proprietaire",
        )

        # Admin user is not propriétaire
        resp = self.admin_client.get("/registre_vehicules_relais/proprietaire")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context["is_proprietaire"])
        self.assertEqual(resp.context["proprietaire_list"].count(), 0)

        # Proprietaire user
        resp = self.proprietaire_client.get("/registre_vehicules_relais/proprietaire")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["is_proprietaire"])
        self.assertEqual(resp.context["proprietaire_list"].count(), 1)

        # Append another proprietaire object to the user
        obj = Proprietaire.objects.create(nom="Another one")
        obj.save()
        obj.users.add(self.proprietaire_user)

        resp = self.proprietaire_client.get("/registre_vehicules_relais/proprietaire")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["is_proprietaire"])
        self.assertEqual(resp.context["proprietaire_list"].count(), 2)


class TestProprietaireCreateView(ClientTestCase):
    def test_view(self):
        client, user = self.create_client()

        resp = client.get("/registre_vehicules_relais/proprietaire/nouveau")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Proprietaire.objects.filter(users__in=[user]).count(), 0)

        resp = client.post(
            "/registre_vehicules_relais/proprietaire/nouveau",
            {
                "nom": "xxx",
                "siret": "11111222223333",
                "telephone": "0609020233",
                "email": "proprietaire@mesads.beta.gouv.fr",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Proprietaire.objects.filter(users__in=[user]).count(), 1)


class TestProprietaireDetailView(ClientTestCase):
    def test_view(self):
        # Proprietaire with vehicules. Cannot be deleted because vehicules are attached to it.
        resp = self.proprietaire_client.get(
            f"/registre_vehicules_relais/proprietaire/{self.proprietaire.id}"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.proprietaire.id, resp.context["object"].id)
        self.assertFalse(resp.context["deletable"])

        # Proprietaire without vehicules
        client, user = self.create_client()
        proprietaire_without_vehicules = Proprietaire.objects.create(
            nom="Propriétaire sans véhicules"
        )
        proprietaire_without_vehicules.users.add(user)
        resp = client.get(
            f"/registre_vehicules_relais/proprietaire/{proprietaire_without_vehicules.id}"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(proprietaire_without_vehicules.id, resp.context["object"].id)
        self.assertTrue(resp.context["deletable"])

        # Admin user should be able to access any proprietaire object
        resp = self.admin_client.get(
            f"/registre_vehicules_relais/proprietaire/{proprietaire_without_vehicules.id}"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(proprietaire_without_vehicules.id, resp.context["object"].id)
        self.assertTrue(resp.context["deletable"])


class TestProprietaireDeleteView(ClientTestCase):
    def test_view(self):
        resp = self.proprietaire_client.post(
            f"/registre_vehicules_relais/proprietaire/{self.proprietaire.id}/supprimer"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["form"].errors["__all__"]), 1)

        for vehicule in Vehicule.objects.all():
            vehicule.delete()

        resp = self.proprietaire_client.post(
            f"/registre_vehicules_relais/proprietaire/{self.proprietaire.id}/supprimer"
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            Proprietaire.objects.filter(id=self.proprietaire.id).count(), 0
        )


class TestProprietaireEditView(ClientTestCase):
    def test_view(self):
        resp = self.proprietaire_client.post(
            f"/registre_vehicules_relais/proprietaire/{self.proprietaire.id}/modifier",
            {
                "nom": "nouveau nom",
                "siret": "99999999999991",
                "telephone": "0600000000",
                "email": "xxxx@yyy.com",
            },
        )
        self.assertEqual(resp.status_code, 302)

        self.proprietaire.refresh_from_db()
        self.assertEqual(self.proprietaire.nom, "nouveau nom")
        self.assertEqual(self.proprietaire.siret, "99999999999991")
        self.assertEqual(self.proprietaire.telephone, "0600000000")
        self.assertEqual(self.proprietaire.email, "xxxx@yyy.com")


class TestProprietaireHistoryView(ClientTestCase):
    def test_view(self):
        resp = self.admin_client.get(
            f"/registre_vehicules_relais/proprietaire/{self.proprietaire.id}/historique"
        )
        self.assertEqual(resp.status_code, 200)
