import datetime
import io

import PyPDF2

from .unittest import ClientTestCase

from mesads.fradm.models import Commune, Prefecture

from mesads.vehicules_relais.models import Proprietaire, Vehicule


class TestIndexView(ClientTestCase):
    def test_200(self):
        resp = self.anonymous_client.get("/relais/")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.headers["Location"], "/relais/consulter")


class TestSearchView(ClientTestCase):
    def test_get(self):
        resp = self.anonymous_client.get("/relais/consulter")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context["is_proprietaire"])

        resp = self.proprietaire_client.get("/relais/consulter")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["is_proprietaire"])

    def test_search(self):
        ain = Prefecture.objects.get(numero="01")
        paris = Prefecture.objects.get(numero="75")

        # Paris
        v1 = Vehicule.objects.create(
            numero="75-01",
            proprietaire=self.proprietaire,
            departement=paris,
            immatriculation="abc-abc-abc",
            modele="Range rover",
            motorisation="essence",
            date_mise_circulation=datetime.date(2020, 5, 1),
            nombre_places=4,
            pmr=True,
            commune_localisation=None,
        )
        v1.save()
        v2 = Vehicule.objects.create(
            numero="75-02",
            proprietaire=self.proprietaire,
            departement=paris,
            immatriculation="def-def-def",
            modele="Range rover",
            motorisation="essence",
            date_mise_circulation=datetime.date(2020, 5, 1),
            nombre_places=4,
            pmr=True,
            commune_localisation=None,
        )
        v2.save()
        # Ain
        v3 = Vehicule.objects.create(
            numero="01-01",
            proprietaire=self.proprietaire,
            departement=ain,
            immatriculation=v1.immatriculation,
            modele="Range rover",
            motorisation="essence",
            date_mise_circulation=datetime.date(2020, 5, 1),
            nombre_places=4,
            pmr=True,
            commune_localisation=None,
        )
        v3.save()

        # 1 vehicule in Ain
        resp = self.admin_client.get(f"/relais/consulter?departement={ain.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["object_list"].count(), 1)

        # 2 vehicules in Paris
        resp = self.admin_client.get(f"/relais/consulter?departement={paris.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["object_list"].count(), 2)

        # 2 vehicule with this immatriculation
        resp = self.admin_client.get(
            f"/relais/consulter?immatriculation={v3.immatriculation}"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["object_list"].count(), 2)

        # Ensure dashes are ignored
        resp = self.admin_client.get(
            f"/relais/consulter?immatriculation={v3.immatriculation.replace('-', '')}"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["object_list"].count(), 2)

        # 1 vehicule with this immatriculation
        resp = self.admin_client.get(
            f"/relais/consulter?immatriculation={v2.immatriculation}"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["object_list"].count(), 1)

        # 1 vehicule with this immatriculation in Paris
        resp = self.admin_client.get(
            f"/relais/consulter?immatriculation={v1.immatriculation}&departement={paris.id}"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["object_list"].count(), 1)

    def test_ordering(self):
        """Ensure vehicules are ordered by numero"""
        paris = Prefecture.objects.get(numero="75")

        resp = self.admin_client.get(f"/relais/consulter?departement={paris.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["object_list"].count(), 0)

        for numero in (
            "75-01",
            "75-02",
            "75-101",
            "75-12",
            "75-03",
        ):
            vehicule = Vehicule.objects.create(
                proprietaire=self.proprietaire,
                departement=paris,
                immatriculation="666-666-666",
                modele="Range rover",
                motorisation="essence",
                date_mise_circulation=datetime.date(2020, 5, 1),
                nombre_places=4,
                pmr=True,
                commune_localisation=None,
            )
            vehicule.numero = numero
            vehicule.save()

        resp = self.admin_client.get(f"/relais/consulter?departement={paris.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["object_list"].count(), 5)
        self.assertEqual(resp.context["object_list"][0].numero, "75-01")
        self.assertEqual(resp.context["object_list"][1].numero, "75-02")
        self.assertEqual(resp.context["object_list"][2].numero, "75-03")
        self.assertEqual(resp.context["object_list"][3].numero, "75-12")
        self.assertEqual(resp.context["object_list"][4].numero, "75-101")


class TestVehiculeView(ClientTestCase):
    def test_get(self):
        vehicule = Vehicule.objects.first()
        for client in self.anonymous_client, self.proprietaire_client:
            resp = client.get(f"/relais/consulter/vehicules/{vehicule.numero}")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.context["vehicule"], vehicule)

            resp = client.get("/relais/consulter/vehicules/33-999")
            self.assertEqual(resp.status_code, 404)


class TestProprietaireListView(ClientTestCase):
    def test_get(self):
        resp = self.anonymous_client.get("/relais/proprietaire")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            resp.headers["Location"],
            "/auth/login/?next=/relais/proprietaire",
        )

        # Admin user is not propriétaire
        resp = self.admin_client.get("/relais/proprietaire")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context["is_proprietaire"])
        self.assertEqual(resp.context["proprietaire_list"].count(), 0)

        # Proprietaire user
        resp = self.proprietaire_client.get("/relais/proprietaire")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["is_proprietaire"])
        self.assertEqual(resp.context["proprietaire_list"].count(), 1)

        # Append another proprietaire object to the user
        obj = Proprietaire.objects.create(nom="Another one")
        obj.save()
        obj.users.add(self.proprietaire_user)

        resp = self.proprietaire_client.get("/relais/proprietaire")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["is_proprietaire"])
        self.assertEqual(resp.context["proprietaire_list"].count(), 2)


class TestProprietaireCreateView(ClientTestCase):
    def test_view(self):
        client, user = self.create_client()

        resp = client.get("/relais/proprietaire/nouveau")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Proprietaire.objects.filter(users__in=[user]).count(), 0)

        resp = client.post(
            "/relais/proprietaire/nouveau",
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
            f"/relais/proprietaire/{self.proprietaire.id}"
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
        resp = client.get(f"/relais/proprietaire/{proprietaire_without_vehicules.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(proprietaire_without_vehicules.id, resp.context["object"].id)
        self.assertTrue(resp.context["deletable"])

        # Admin user should be able to access any proprietaire object
        resp = self.admin_client.get(
            f"/relais/proprietaire/{proprietaire_without_vehicules.id}"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(proprietaire_without_vehicules.id, resp.context["object"].id)
        self.assertTrue(resp.context["deletable"])

    def test_ordering(self):
        """Ensure vehicules are ordered by numero"""
        proprietaire = Proprietaire.objects.create(nom="Propriétaire sans véhicules")
        resp = self.admin_client.get(f"/relais/proprietaire/{proprietaire.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["object_list"].count(), 0)

        paris = Prefecture.objects.filter(numero="75").get()
        for numero in (
            "75-01",
            "75-02",
            "75-101",
            "75-12",
            "75-03",
        ):
            vehicule = Vehicule.objects.create(
                proprietaire=proprietaire,
                departement=paris,
                immatriculation="666-666-666",
                modele="Range rover",
                motorisation="essence",
                date_mise_circulation=datetime.date(2020, 5, 1),
                nombre_places=4,
                pmr=True,
                commune_localisation=None,
            )
            vehicule.numero = numero
            vehicule.save()

        resp = self.admin_client.get(f"/relais/proprietaire/{proprietaire.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["object_list"].count(), 5)
        self.assertEqual(resp.context["object_list"][0].numero, "75-01")
        self.assertEqual(resp.context["object_list"][1].numero, "75-02")
        self.assertEqual(resp.context["object_list"][2].numero, "75-03")
        self.assertEqual(resp.context["object_list"][3].numero, "75-12")
        self.assertEqual(resp.context["object_list"][4].numero, "75-101")


class TestProprietaireDeleteView(ClientTestCase):
    def test_view(self):
        resp = self.proprietaire_client.post(
            f"/relais/proprietaire/{self.proprietaire.id}/supprimer"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["form"].errors["__all__"]), 1)

        for vehicule in Vehicule.objects.all():
            vehicule.delete()

        resp = self.proprietaire_client.post(
            f"/relais/proprietaire/{self.proprietaire.id}/supprimer"
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            Proprietaire.objects.filter(id=self.proprietaire.id).count(), 0
        )


class TestProprietaireEditView(ClientTestCase):
    def test_view(self):
        resp = self.proprietaire_client.post(
            f"/relais/proprietaire/{self.proprietaire.id}/modifier",
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
            f"/relais/proprietaire/{self.proprietaire.id}/historique"
        )
        self.assertEqual(resp.status_code, 200)


class TestProprietaireVehiculeCreateView(ClientTestCase):
    def test_view(self):
        departement = Prefecture.objects.first()
        commune = Commune.objects.first()
        count = Vehicule.objects.count()
        resp = self.proprietaire_client.post(
            f"/relais/proprietaire/{self.proprietaire.id}/nouveau_vehicule",
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
            f"/relais/proprietaire/{self.proprietaire.id}/vehicules/{vehicule.numero}",
        )
        self.assertEqual(resp.status_code, 200)

        commune = Commune.objects.first()
        resp = self.proprietaire_client.post(
            f"/relais/proprietaire/{self.proprietaire.id}/vehicules/{vehicule.numero}",
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
            f"/relais/proprietaire/{self.proprietaire.id}/vehicules/{vehicule.numero}",
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
            f"/relais/proprietaire/{self.proprietaire.id}/vehicules/{vehicule.numero}/supprimer"
        )
        self.assertEqual(resp.status_code, 200)

        resp = self.proprietaire_client.post(
            f"/relais/proprietaire/{self.proprietaire.id}/vehicules/{vehicule.numero}/supprimer"
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
            f"/relais/proprietaire/{self.proprietaire.id}/vehicules/{vehicule.numero}/historique"
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            resp.headers["Location"],
            f"/admin/login/?next=/relais/proprietaire/{self.proprietaire.id}/vehicules/{vehicule.numero}/historique",
        )

        # ok
        resp = self.admin_client.get(
            f"/relais/proprietaire/{self.proprietaire.id}/vehicules/{vehicule.numero}/historique"
        )
        self.assertEqual(resp.status_code, 200)


class TestProprietaireVehiculeRecepisseView(ClientTestCase):
    def test_view(self):
        departement = Prefecture.objects.first()
        vehicule = Vehicule.objects.create(
            proprietaire=self.proprietaire,
            departement=departement,
        )
        resp = self.admin_client.get(
            f"/relais/proprietaire/{self.proprietaire.id}/vehicules/{vehicule.numero}/recepisse"
        )
        self.assertEqual(resp.status_code, 200)

        pdf = io.BytesIO(resp.content)
        reader = PyPDF2.PdfReader(pdf)
        # Make sure there are only 2 pages in the PDF generated
        self.assertEqual(len(reader.pages), 2)
