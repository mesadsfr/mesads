from ..unittest import ClientTestCase


class TestCommuneAutocompleteView(ClientTestCase):
    def test_get_queryset_anonymous(self):
        resp = self.anonymous_client.get("/fradm/commune/autocomplete")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["results"]), len(self.COMMUNES))

    def test_get_queryset_logged(self):
        resp = self.auth_client.get("/fradm/commune/autocomplete")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["results"]), len(self.COMMUNES))

        resp = self.auth_client.get("/fradm/commune/autocomplete?q=sdoifnadisofanio")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["results"]), 0)

        resp = self.auth_client.get("/fradm/commune/autocomplete?q=paris")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            len(resp.json()["results"]),
            sum(1 for entry in self.COMMUNES if "paris" in entry[2].lower()),
        )

        # Accents should be ignored
        resp = self.auth_client.get("/fradm/commune/autocomplete?q=parìs")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            len(resp.json()["results"]),
            sum(1 for entry in self.COMMUNES if "paris" in entry[2].lower()),
        )

        resp = self.auth_client.get("/fradm/commune/autocomplete?q=97")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            len(resp.json()["results"]),
            sum(1 for entry in self.COMMUNES if entry[1].startswith("97")),
        )

    def test_queryset_with_departement_logged(self):
        resp = self.auth_client.get("/fradm/commune/75/autocomplete")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["results"]), 1)
        self.assertIn("paris", resp.json()["results"][0]["text"].lower())

        resp = self.auth_client.get("/fradm/commune/75/autocomplete?q=paris")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["results"]), 1)
        self.assertIn("paris", resp.json()["results"][0]["text"].lower())

        resp = self.auth_client.get("/fradm/commune/75/autocomplete?q=xxxx")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["results"]), 0)


class TestEPCIAutocompleteView(ClientTestCase):
    def test_get_queryset_anonymous(self):
        resp = self.anonymous_client.get("/fradm/epci/autocomplete")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["results"]), len(self.EPCI))

    def test_get_queryset_logged(self):
        resp = self.auth_client.get("/fradm/epci/autocomplete")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["results"]), len(self.EPCI))

        resp = self.auth_client.get("/fradm/epci/autocomplete?q=pa23noianr")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["results"]), 0)

        resp = self.auth_client.get("/fradm/epci/autocomplete?q=ROISSY")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            len(resp.json()["results"]),
            sum(1 for entry in self.EPCI if "roissy" in entry[2].lower()),
        )

        # Accents should be ignored
        resp = self.auth_client.get("/fradm/epci/autocomplete?q=RÔISSY")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            len(resp.json()["results"]),
            sum(1 for entry in self.EPCI if "roissy" in entry[2].lower()),
        )

        # Filter by departement
        resp = self.auth_client.get("/fradm/epci/01/autocomplete")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            len(resp.json()["results"]),
            len([True for id, departement, name in self.EPCI if departement == "01"]),
        )


class TestPrefectureAutocompleteView(ClientTestCase):
    def test_get_queryset_anonymous(self):
        resp = self.anonymous_client.get("/fradm/prefecture/autocomplete")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["results"]), len(self.PREFECTURES))

    def test_get_queryset_logged(self):
        resp = self.auth_client.get("/fradm/prefecture/autocomplete")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["results"]), len(self.PREFECTURES))

        resp = self.auth_client.get("/fradm/prefecture/autocomplete?q=xxx")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["results"]), 0)

        resp = self.auth_client.get("/fradm/prefecture/autocomplete?q=paris")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            len(resp.json()["results"]),
            sum(1 for entry in self.PREFECTURES if "paris" in entry[1].lower()),
        )

        # Accents should be ignored
        resp = self.auth_client.get("/fradm/prefecture/autocomplete?q=pàrìs")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            len(resp.json()["results"]),
            sum(1 for entry in self.PREFECTURES if "paris" in entry[1].lower()),
        )
