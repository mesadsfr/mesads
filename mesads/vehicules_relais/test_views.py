import datetime

from .unittest import ClientTestCase

from mesads.fradm.models import Commune, Prefecture

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


class TestProprietaireVehiculeCreateView(ClientTestCase):
    def test_view(self):
        departement = Prefecture.objects.first()
        commune = Commune.objects.first()
        count = Vehicule.objects.count()
        resp = self.proprietaire_client.post(
            f"/registre_vehicules_relais/proprietaire/{self.proprietaire.id}/nouveau_vehicule",
            {
                "immatriculation": "XXX-YYY",
                "modele": "Peugeot 308",
                "motorisation": "diesel",
                "date_mise_circulation": "2020-11-19",
                "nombre_places": "4",
                "pmr": "off",
                "commune_localisation": commune.id,
                "departement": departement.id,
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Vehicule.objects.count(), count + 1)


class TestProprietaireVehiculeUpdateView(ClientTestCase):
    def test_view(self):
        departement = Prefecture.objects.first()
        vehicule = Vehicule.objects.create(
            proprietaire=self.proprietaire,
            departement=departement,
        )

        resp = self.proprietaire_client.get(
            f"/registre_vehicules_relais/proprietaire/{self.proprietaire.id}/vehicules/{vehicule.numero}",
        )
        self.assertEqual(resp.status_code, 200)

        commune = Commune.objects.first()
        resp = self.proprietaire_client.post(
            f"/registre_vehicules_relais/proprietaire/{self.proprietaire.id}/vehicules/{vehicule.numero}",
            {
                "immatriculation": "XXX-YYY",
                "modele": "Peugeot 308",
                "motorisation": "diesel",
                "date_mise_circulation": "2020-11-19",
                "nombre_places": "4",
                "pmr": True,
                "commune_localisation": commune.id,
            },
        )
        self.assertEqual(resp.status_code, 302)
        vehicule.refresh_from_db()

        self.assertEqual(vehicule.immatriculation, "XXX-YYY")
        self.assertEqual(vehicule.modele, "Peugeot 308")
        self.assertEqual(vehicule.motorisation, "diesel")
        self.assertEqual(vehicule.date_mise_circulation, datetime.date(2020, 11, 19))
        self.assertEqual(vehicule.nombre_places, 4)
        self.assertTrue(vehicule.pmr)
        self.assertEqual(vehicule.commune_localisation, commune)

        # It is impossible to update the departement of a vehicule once it is
        # created. The field "departement" is ignored.
        other_departement = Prefecture.objects.create(
            numero="94", libelle="Val de Marne"
        )
        resp = self.proprietaire_client.post(
            f"/registre_vehicules_relais/proprietaire/{self.proprietaire.id}/vehicules/{vehicule.numero}",
            {
                "immatriculation": "XXX-YYY",
                "modele": "Peugeot 308",
                "motorisation": "diesel",
                "date_mise_circulation": "2020-11-19",
                "nombre_places": "4",
                "pmr": "true",
                "commune_localisation": commune.id,
                "departement": other_departement.id,
            },
        )
        self.assertEqual(resp.status_code, 302)
        vehicule.refresh_from_db()
        self.assertEqual(vehicule.departement, departement)


class TestProprietaireVehiculeDeleteView(ClientTestCase):
    def test_view(self):
        departement = Prefecture.objects.first()
        vehicule = Vehicule.objects.create(
            proprietaire=self.proprietaire,
            departement=departement,
        )

        resp = self.proprietaire_client.get(
            f"/registre_vehicules_relais/proprietaire/{self.proprietaire.id}/vehicules/{vehicule.numero}/supprimer"
        )
        self.assertEqual(resp.status_code, 200)

        resp = self.proprietaire_client.post(
            f"/registre_vehicules_relais/proprietaire/{self.proprietaire.id}/vehicules/{vehicule.numero}/supprimer"
        )
        self.assertEqual(resp.status_code, 302)
        vehicule.refresh_from_db()
        self.assertIsNotNone(vehicule.deleted_at)


class TestProprietaireVehiculeHistoryView(ClientTestCase):
    def test_view(self):
        departement = Prefecture.objects.first()
        vehicule = Vehicule.objects.create(
            proprietaire=self.proprietaire,
            departement=departement,
        )
        # only available for admins
        resp = self.proprietaire_client.get(
            f"/registre_vehicules_relais/proprietaire/{self.proprietaire.id}/vehicules/{vehicule.numero}/historique"
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            resp.headers["Location"],
            f"/admin/login/?next=/registre_vehicules_relais/proprietaire/{self.proprietaire.id}/vehicules/{vehicule.numero}/historique",
        )

        # ok
        resp = self.admin_client.get(
            f"/registre_vehicules_relais/proprietaire/{self.proprietaire.id}/vehicules/{vehicule.numero}/historique"
        )
        self.assertEqual(resp.status_code, 200)
