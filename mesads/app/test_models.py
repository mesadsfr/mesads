from django.core.exceptions import ValidationError
from django.test import override_settings, TestCase

import requests
import requests_mock

from .models import ADS, validate_siret, ADSUser
from .unittest import ClientTestCase


class TestADSManager(ClientTestCase):
    def test_str(self):
        self.assertIn('commune', str(self.ads_manager_city35))
        self.assertIn('Melesse', str(self.ads_manager_city35))


class TestADSManagerRequest(ClientTestCase):
    def test_str(self):
        self.assertIn(self.ads_manager_request.user.email, str(self.ads_manager_request))


class TestADSManagerAdministrator(ClientTestCase):
    def test_str(self):
        self.assertIn(self.ads_manager_administrator_35.prefecture.libelle, str(self.ads_manager_administrator_35))


class TestValidateSiret(TestCase):
    def test_validate_siret(self):
        self.assertRaises(ValidationError, validate_siret, '1234')

        # Insee token not set, no verification
        self.assertIsNone(validate_siret('12345678912345'))

    @override_settings(INSEE_TOKEN='xxx')
    def test_validate_siret_insee(self):
        siret = '12345678901234'
        api_url = f'https://api.insee.fr/entreprises/sirene/V3/siret/{siret}'

        with requests_mock.Mocker() as m:
            # Setup mock to return return HTTP/200: valid SIRET
            m.get(api_url)
            self.assertIsNone(validate_siret(siret))

            # Setup mock to return return HTTP/404: invalid SIRET
            m.get(api_url, status_code=404)
            self.assertRaises(ValidationError, validate_siret, siret)

            # Setup mock to return return timeout: SIRET is not checked
            m.get(api_url, exc=requests.exceptions.ConnectTimeout)
            self.assertIsNone(validate_siret(siret))

            # Setup mock to return unexpected response from INSEE api
            m.get(api_url, status_code=500)
            with self.assertLogs(logger='', level='ERROR') as cm:
                self.assertIsNone(validate_siret(siret))
                self.assertEqual(len(cm.records), 1)


class TestADS(ClientTestCase):
    def setUp(self):
        super().setUp()
        self.ads = ADS.objects.create(number='12346', ads_manager=self.ads_manager_city35)

    def test_str(self):
        self.assertIn(str(self.ads.id), str(self.ads))

    def test_get_legal_filename(self):
        filename = self.ads.get_legal_filename('my_filename')
        self.assertIn('my_filename', filename)


class TestADSUser(ClientTestCase):
    def setUp(self):
        super().setUp()
        self.ads = ADS.objects.create(number='12346', ads_manager=self.ads_manager_city35)

    def test_str(self):
        ads_user = ADSUser.objects.create(ads=self.ads, name='Bob')
        self.assertEqual(str(ads_user), 'Bob')
