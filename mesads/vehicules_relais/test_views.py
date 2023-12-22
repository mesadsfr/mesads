from .unittest import ClientTestCase

from mesads.fradm.models import Prefecture


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
