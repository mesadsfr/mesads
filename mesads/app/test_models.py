from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import validate_siret
from .unittest import ClientTestCase


class TestADSManager(ClientTestCase):
    def test_str(self):
        self.assertIn('commune', str(self.ads_manager_city35))
        self.assertIn('Melesse', str(self.ads_manager_city35))

    def test_get_administrators_users(self):
        self.assertEqual(len(self.ads_manager_city35.get_administrators_users()), 1)



class TestADSManagerRequest(ClientTestCase):
    def test_str(self):
        self.assertIn(self.ads_manager_request.user.email, str(self.ads_manager_request))


class TestADSManagerAdministrator(ClientTestCase):
    def test_str(self):
        self.assertIn(self.ads_manager_administrator_35.prefecture.libelle, str(self.ads_manager_administrator_35))
