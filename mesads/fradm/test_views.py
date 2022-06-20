from mesads.users.unittest import ClientTestCase

from .models import Commune, EPCI, Prefecture


class TestCommuneAutocompleteView(ClientTestCase):
    def setUp(self):
        super().setUp()
        for insee, departement, libelle in (
            ('13055', '13', 'Marseille'),
            ('75056', '76', 'Paris'),
            ('97616', '976', 'Sada'),
            ('97617', '976', 'Tsingoni'),
        ):
            Commune.objects.create(insee=insee, departement=departement, libelle=libelle)

    def test_get_queryset_anonymous(self):
        resp = self.anonymous_client.get('/fradm/commune/autocomplete')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['results'], [])

    def test_get_queryset_logged(self):
        resp = self.auth_client.get('/fradm/commune/autocomplete')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()['results']), 4)

        resp = self.auth_client.get('/fradm/commune/autocomplete?q=sdoifnadisofanio')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()['results']), 0)

        resp = self.auth_client.get('/fradm/commune/autocomplete?q=par')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()['results']), 1)
        self.assertIn('Paris', resp.json()['results'][0]['text'])

        resp = self.auth_client.get('/fradm/commune/autocomplete?q=97')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()['results']), 2)
        self.assertIn('Sada', resp.json()['results'][0]['text'])
        self.assertIn('Tsingoni', resp.json()['results'][1]['text'])


class TestEPCIAutocompleteView(ClientTestCase):
    def setUp(self):
        super().setUp()
        for siren, departement, name in (
            ('200029999', '1', "CC Rives de l'Ain - Pays du Cerdon"),
            ('200040350', '1', "CC Bugey Sud"),
            ('200055655', '95', "CA Roissy Pays de France"),
        ):
            EPCI.objects.create(siren=siren, departement=departement, name=name)

    def test_get_queryset_anonymous(self):
        resp = self.anonymous_client.get('/fradm/epci/autocomplete')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['results'], [])

    def test_get_queryset_logged(self):
        resp = self.auth_client.get('/fradm/epci/autocomplete')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()['results']), 3)

        resp = self.auth_client.get('/fradm/epci/autocomplete?q=par')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()['results']), 0)

        resp = self.auth_client.get('/fradm/epci/autocomplete?q=ROISSY')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()['results']), 1)
        self.assertIn('Roissy', resp.json()['results'][0]['text'])


class TestPrefectureAutocompleteView(ClientTestCase):
    def setUp(self):
        super().setUp()
        for numero, libelle in (
            ('01', 'Ain'),
            ('33', 'Gironde'),
            ('73', 'Savoie'),
            ('75', 'Préfecture de Police de Paris'),
        ):
            Prefecture.objects.create(numero=numero, libelle=libelle)

    def test_get_queryset_anonymous(self):
        resp = self.anonymous_client.get('/fradm/prefecture/autocomplete')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['results'], [])

    def test_get_queryset_logged(self):
        resp = self.auth_client.get('/fradm/prefecture/autocomplete')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()['results']), 4)

        resp = self.auth_client.get('/fradm/prefecture/autocomplete?q=xxx')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()['results']), 0)

        resp = self.auth_client.get('/fradm/prefecture/autocomplete?q=paris')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()['results']), 1)
        self.assertIn('Paris', resp.json()['results'][0]['text'])
