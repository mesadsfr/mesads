from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework.test import APIClient

from mesads.app.models import ADSUpdateFile
from mesads.app.unittest import ClientTestCase


class TestADSUpdatesViewSet(ClientTestCase):
    def test_get(self):
        client = APIClient()

        # Not authenticated
        resp = client.get('/api/ads-updates/')
        self.assertEqual(resp.status_code, 401)

        # Authenticated, empty list
        client.force_authenticate(user=self.admin_user)
        resp = client.get('/api/ads-updates/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {
            'count': 0,
            'next': None,
            'previous': None,
            'results': []
        })

        # Two files, but only one for the admin user
        ADSUpdateFile.objects.create(
            user=self.admin_user
        )
        ADSUpdateFile.objects.create(
            user=self.ads_manager_administrator_35_user
        )
        resp = client.get('/api/ads-updates/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['count'], 1)

    def test_post(self):
        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        update_file = SimpleUploadedFile(
            name='myfile.pdf',
            content=b'ADS_CONTENT',
            content_type='applicaiton/pdf'
        )
        resp = client.post('/api/ads-updates/', {
            'update_file': update_file,
        })

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(ADSUpdateFile.objects.count(), 1)
        self.assertEqual(ADSUpdateFile.objects.all()[0].imported, False)
        self.assertEqual(ADSUpdateFile.objects.all()[0].update_file.read(), b'ADS_CONTENT')
