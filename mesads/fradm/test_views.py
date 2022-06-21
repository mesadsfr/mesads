from .unittest import ClientTestCase


class TestCommuneAutocompleteView(ClientTestCase):
    def test_get_queryset_anonymous(self):
        resp = self.anonymous_client.get('/fradm/commune/autocomplete')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['results'], [])

    def test_get_queryset_logged(self):
        resp = self.auth_client.get('/fradm/commune/autocomplete')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()['results']), len(self.COMMUNES))

        resp = self.auth_client.get('/fradm/commune/autocomplete?q=sdoifnadisofanio')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()['results']), 0)

        resp = self.auth_client.get('/fradm/commune/autocomplete?q=paris')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            len(resp.json()['results']),
            sum(1 for entry in self.COMMUNES if 'paris' in entry[2].lower())
        )

        resp = self.auth_client.get('/fradm/commune/autocomplete?q=97')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            len(resp.json()['results']),
            sum(1 for entry in self.COMMUNES if entry[1].startswith('97'))
        )


class TestEPCIAutocompleteView(ClientTestCase):
    def test_get_queryset_anonymous(self):
        resp = self.anonymous_client.get('/fradm/epci/autocomplete')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['results'], [])

    def test_get_queryset_logged(self):
        resp = self.auth_client.get('/fradm/epci/autocomplete')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()['results']), len(self.EPCI))

        resp = self.auth_client.get('/fradm/epci/autocomplete?q=pa23noianr')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()['results']), 0)

        resp = self.auth_client.get('/fradm/epci/autocomplete?q=ROISSY')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            len(resp.json()['results']),
            sum(1 for entry in self.EPCI if 'roissy' in entry[2].lower())
        )


class TestPrefectureAutocompleteView(ClientTestCase):
    def test_get_queryset_anonymous(self):
        resp = self.anonymous_client.get('/fradm/prefecture/autocomplete')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['results'], [])

    def test_get_queryset_logged(self):
        resp = self.auth_client.get('/fradm/prefecture/autocomplete')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()['results']), len(self.PREFECTURES))

        resp = self.auth_client.get('/fradm/prefecture/autocomplete?q=xxx')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()['results']), 0)

        resp = self.auth_client.get('/fradm/prefecture/autocomplete?q=paris')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            len(resp.json()['results']),
            sum(1 for entry in self.PREFECTURES if 'paris' in entry[1].lower())
        )
