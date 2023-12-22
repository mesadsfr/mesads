from .unittest import ClientTestCase


class TestIndexView(ClientTestCase):
    def test_200(self):
        resp = self.anonymous_client.get("/registre_vehicules_relais/")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            resp.headers["Location"], "/registre_vehicules_relais/consulter"
        )
