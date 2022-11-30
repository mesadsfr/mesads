from datetime import timedelta

from django.contrib import messages
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Q
from django.test import RequestFactory
from django.utils import timezone

from mesads.fradm.models import Commune, EPCI, Prefecture

from .models import (
    ADS,
    ADSLegalFile,
    ADSManagerRequest,
    ADSUser,
    validate_siret,
)
from .unittest import ClientTestCase
from .views import DashboardsView, DashboardsDetailView


class TestHomepageView(ClientTestCase):
    def test_redirection(self):
        for client_name, client, expected_status, redirect_url in (
            ('anonymous', self.anonymous_client, 302, '/auth/login/?next=/'),
            ('auth', self.auth_client, 302, '/gestion'),
            ('ads_manager 35', self.ads_manager_city35_client, 302, '/gestion'),
            ('ads_manager_admin 35', self.ads_manager_administrator_35_client, 302, '/admin_gestion'),
            ('admin', self.admin_client, 302, '/dashboards'),
        ):
            with self.subTest(client_name=client_name, expected_status=expected_status, redirect_url=redirect_url):
                resp = client.get('/')
                self.assertEqual(resp.status_code, expected_status)
                self.assertEqual(resp.url, redirect_url)


class TestADSManagerAdminView(ClientTestCase):
    def setUp(self):
        super().setUp()
        self.ads_manager_request = ADSManagerRequest.objects.create(
            user=self.create_user().obj,
            ads_manager=self.ads_manager_city35,
            accepted=None
        )

    def test_permissions(self):
        for client_name, client, expected_status in (
            ('admin', self.admin_client, 200),
            ('anonymous', self.anonymous_client, 302),
            ('auth', self.auth_client, 404),
            ('ads_manager 35', self.ads_manager_city35_client, 404),
            ('ads_manager_admin 35', self.ads_manager_administrator_35_client, 200),
        ):
            with self.subTest(client_name=client_name, expected_status=expected_status):
                resp = client.get('/admin_gestion')
                self.assertEqual(resp.status_code, expected_status)

    def test_invalid_action(self):
        resp = self.ads_manager_administrator_35_client.post(
            '/admin_gestion',
            {'action': 'xxx', 'request_id': 1}
        )
        self.assertEqual(resp.status_code, 400)

    def test_invalid_request_id(self):
        resp = self.ads_manager_administrator_35_client.post(
            '/admin_gestion',
            {'action': 'accept', 'request_id': 12342}
        )
        self.assertEqual(resp.status_code, 404)

    def test_accept(self):
        self.assertEqual(len(mail.outbox), 0)

        resp = self.ads_manager_administrator_35_client.post(
            '/admin_gestion',
            {'action': 'accept', 'request_id': self.ads_manager_request.id}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/admin_gestion')
        self.ads_manager_request.refresh_from_db()
        self.assertTrue(self.ads_manager_request.accepted)
        self.assertEqual(len(mail.outbox), 1)

    def test_deny(self):
        self.assertEqual(len(mail.outbox), 0)

        resp = self.ads_manager_administrator_35_client.post(
            '/admin_gestion',
            {'action': 'deny', 'request_id': self.ads_manager_request.id}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/admin_gestion')
        self.ads_manager_request.refresh_from_db()
        self.assertFalse(self.ads_manager_request.accepted)
        self.assertEqual(len(mail.outbox), 1)


class TestADSManagerRequestView(ClientTestCase):
    def setUp(self):
        super().setUp()
        self.initial_ads_managers_count = ADSManagerRequest.objects.count()

    def test_permissions(self):
        for client_name, client, expected_status in (
            ('anonymous', self.anonymous_client, 302),
            ('auth', self.auth_client, 200),
            ('ads_manager 35', self.ads_manager_city35_client, 200),
            ('ads_manager_admin 35', self.ads_manager_administrator_35_client, 200),
        ):
            with self.subTest(client_name=client_name, expected_status=expected_status):
                resp = client.get('/gestion')
                self.assertEqual(resp.status_code, expected_status)

    def test_create_request_invalid_id(self):
        """Provide the id of a non-existing object."""
        resp = self.auth_client.post('/gestion', {
            'commune': 9999
        })
        self.assertIn('error', resp.content.decode('utf8'))

    def test_create_request_commune(self):
        resp = self.auth_client.post('/gestion', {
            'commune': self.commune_melesse.id
        })
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn('error', resp.content.decode('utf8'))
        self.assertEqual(ADSManagerRequest.objects.count(), self.initial_ads_managers_count + 1)

        # Make sure django message is in the next request
        resp = self.auth_client.get('/gestion')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['messages']), 1)
        self.assertEqual(
            list(resp.context['messages'])[0].level,
            messages.SUCCESS
        )

        # If there is a ADSManagerAdministrator related to the commune, an email is sent for each member.
        # The base class ClientTestCase configures Melesse to be managed by the ADSManagerAdministrator entry of
        # l'Ille-et-Vilaine.
        self.assertEqual(len(mail.outbox), 1)

        #
        # If we send the same request, a warning message is displayed and no email is sent.
        #
        resp = self.auth_client.post('/gestion', {
            'commune': self.commune_melesse.id
        })
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn('error', resp.content.decode('utf8'))
        self.assertEqual(ADSManagerRequest.objects.count(), self.initial_ads_managers_count + 1)

        # Check warning message
        resp = self.auth_client.get('/gestion')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['messages']), 1)
        self.assertEqual(
            list(resp.context['messages'])[0].level,
            messages.WARNING
        )
        # No new email
        self.assertEqual(len(mail.outbox), 1)

    def test_create_request_epci(self):
        epci = EPCI.objects.first()
        resp = self.auth_client.post('/gestion', {
            'epci': epci.id
        })
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn('error', resp.content.decode('utf8'))
        self.assertEqual(ADSManagerRequest.objects.count(), self.initial_ads_managers_count + 1)

        # Make sure django message is in the next request
        resp = self.auth_client.get('/gestion')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['messages']), 1)
        self.assertEqual(
            list(resp.context['messages'])[0].level,
            messages.SUCCESS
        )

        #
        # If we send the same request, no object is created and a warning message is displayed.
        #
        resp = self.auth_client.post('/gestion', {
            'epci': epci.id
        })
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn('error', resp.content.decode('utf8'))
        self.assertEqual(ADSManagerRequest.objects.count(), self.initial_ads_managers_count + 1)

        resp = self.auth_client.get('/gestion')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['messages']), 1)
        self.assertEqual(
            list(resp.context['messages'])[0].level,
            messages.WARNING
        )

    def test_create_request_prefecture(self):
        prefecture = Prefecture.objects.first()
        resp = self.auth_client.post('/gestion', {
            'prefecture': prefecture.id
        })
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn('error', resp.content.decode('utf8'))
        self.assertEqual(ADSManagerRequest.objects.count(), self.initial_ads_managers_count + 1)

        # Make sure django message is in the next request
        resp = self.auth_client.get('/gestion')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['messages']), 1)
        self.assertEqual(
            list(resp.context['messages'])[0].level,
            messages.SUCCESS
        )

        #
        # If we send the same request, no object is created and a warning message is displayed.
        #
        resp = self.auth_client.post('/gestion', {
            'prefecture': prefecture.id
        })
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn('error', resp.content.decode('utf8'))
        self.assertEqual(ADSManagerRequest.objects.count(), self.initial_ads_managers_count + 1)

        # Make sure django message is in the next request
        resp = self.auth_client.get('/gestion')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['messages']), 1)
        self.assertEqual(
            list(resp.context['messages'])[0].level,
            messages.WARNING
        )


class TestADSManagerView(ClientTestCase):
    def test_permissions(self):
        for client_name, client, expected_status in (
            ('anonymous', self.anonymous_client, 302),
            ('auth', self.auth_client, 404),
            ('ads_manager 35', self.ads_manager_city35_client, 200),
            ('ads_manager_admin 35', self.ads_manager_administrator_35_client, 200),
        ):
            with self.subTest(client_name=client_name, expected_status=expected_status):
                resp = client.get(f'/gestion/{self.ads_manager_city35.id}/')
                self.assertEqual(resp.status_code, expected_status)

    def test_get_404(self):
        resp = self.ads_manager_city35_client.get('/gestion/99999/')
        self.assertEqual(resp.status_code, 404)

    def test_get(self):
        resp = self.ads_manager_city35_client.get(
            f'/gestion/{self.ads_manager_city35.id}/'
        )
        self.assertIn(self.ads_manager_city35.content_object.libelle, resp.content.decode('utf8'))

    def test_filters(self):
        """Test filtering"""
        # ADS 1
        ADS.objects.create(
            number='FILTER1', ads_manager=self.ads_manager_city35,
            immatriculation_plate='imm4tri-cul4tion',
            accepted_cpam=True
        )
        # ADS 2
        ADS.objects.create(
            number='FILTER2', ads_manager=self.ads_manager_city35,
            owner_name='Bob Dylan',
            accepted_cpam=False
        )
        # ADS 3
        ads3 = ADS.objects.create(
            number='FILTER3', ads_manager=self.ads_manager_city35,
            owner_siret='12312312312312'
        )
        ADSUser.objects.create(
            ads=ads3, name='Henri super',
            siret='11111111111111'
        )
        # ADS 4
        ads4 = ADS.objects.create(
            number='FILTER4', ads_manager=self.ads_manager_city35
        )
        ADSUser.objects.create(
            ads=ads4,
            name='Matthieu pas super',
            siret='22222222222222'
        )

        # Immatriculatin plate, returns first ADS
        resp = self.ads_manager_city35_client.get(
            f'/gestion/{self.ads_manager_city35.id}/?q=imm4tricul4tion'
        )
        self.assertIn('FILTER1', resp.content.decode('utf8'))
        self.assertNotIn('FILTER2', resp.content.decode('utf8'))
        self.assertNotIn('FILTER3', resp.content.decode('utf8'))
        self.assertNotIn('FILTER4', resp.content.decode('utf8'))

        # Owner firstname/lastname, returns second ADS
        resp = self.ads_manager_city35_client.get(
            f'/gestion/{self.ads_manager_city35.id}/?q=bob dyla'
        )
        self.assertNotIn('FILTER1', resp.content.decode('utf8'))
        self.assertIn('FILTER2', resp.content.decode('utf8'))
        self.assertNotIn('FILTER3', resp.content.decode('utf8'))
        self.assertNotIn('FILTER4', resp.content.decode('utf8'))

        # Owner SIRET, return third ADS
        resp = self.ads_manager_city35_client.get(
            f'/gestion/{self.ads_manager_city35.id}/?q=123123123'
        )
        self.assertNotIn('FILTER1', resp.content.decode('utf8'))
        self.assertNotIn('FILTER2', resp.content.decode('utf8'))
        self.assertIn('FILTER3', resp.content.decode('utf8'))
        self.assertNotIn('FILTER4', resp.content.decode('utf8'))

        # User SIRET, return ADS 4
        resp = self.ads_manager_city35_client.get(
            f'/gestion/{self.ads_manager_city35.id}/?q=22222222222222'
        )
        self.assertNotIn('FILTER1', resp.content.decode('utf8'))
        self.assertNotIn('FILTER2', resp.content.decode('utf8'))
        self.assertNotIn('FILTER3', resp.content.decode('utf8'))
        self.assertIn('FILTER4', resp.content.decode('utf8'))

        # User name, return ADS 3
        resp = self.ads_manager_city35_client.get(
            f'/gestion/{self.ads_manager_city35.id}/?q=Henri SUPER'
        )
        self.assertNotIn('FILTER1', resp.content.decode('utf8'))
        self.assertNotIn('FILTER2', resp.content.decode('utf8'))
        self.assertIn('FILTER3', resp.content.decode('utf8'))
        self.assertNotIn('FILTER4', resp.content.decode('utf8'))

        # CPAM accepted true, return ads 1
        resp = self.ads_manager_city35_client.get(
            f'/gestion/{self.ads_manager_city35.id}/?accepted_cpam=True'
        )
        self.assertIn('FILTER1', resp.content.decode('utf8'))
        self.assertNotIn('FILTER2', resp.content.decode('utf8'))
        self.assertNotIn('FILTER3', resp.content.decode('utf8'))
        self.assertNotIn('FILTER4', resp.content.decode('utf8'))

        # CPAM accepted false, return ads 2
        resp = self.ads_manager_city35_client.get(
            f'/gestion/{self.ads_manager_city35.id}/?accepted_cpam=False'
        )
        self.assertNotIn('FILTER1', resp.content.decode('utf8'))
        self.assertIn('FILTER2', resp.content.decode('utf8'))
        self.assertNotIn('FILTER3', resp.content.decode('utf8'))
        self.assertNotIn('FILTER4', resp.content.decode('utf8'))

        # CPAM accepted any, and no filters, return all
        resp = self.ads_manager_city35_client.get(
            f'/gestion/{self.ads_manager_city35.id}/?q=&accepted_cpam='
        )
        self.assertIn('FILTER1', resp.content.decode('utf8'))
        self.assertIn('FILTER2', resp.content.decode('utf8'))
        self.assertIn('FILTER3', resp.content.decode('utf8'))
        self.assertIn('FILTER4', resp.content.decode('utf8'))


class TestADSView(ClientTestCase):
    def setUp(self):
        super().setUp()
        self.ads = ADS.objects.create(number='12346', ads_manager=self.ads_manager_city35)

    def test_permissions(self):
        for client_name, client, expected_status in (
            ('anonymous', self.anonymous_client, 302),
            ('auth', self.auth_client, 404),
            ('ads_manager 35', self.ads_manager_city35_client, 200),
            ('ads_manager_admin 35', self.ads_manager_administrator_35_client, 200),
        ):
            with self.subTest(client_name=client_name, expected_status=expected_status):
                resp = client.get(f'/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}')
                self.assertEqual(resp.status_code, expected_status)

    def test_get_404(self):
        resp = self.ads_manager_city35_client.get(f'/gestion/{self.ads_manager_city35.id}/ads/999')
        self.assertEqual(resp.status_code, 404)

    def test_invalid_form(self):
        """ADSUserFormSet is not provided, error should be rendered."""
        resp = self.ads_manager_city35_client.post(
            f'/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}',
            {
                'number': self.ads.id,
                'owner_name': 'Jean-Jacques Goldman',
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn('TOTAL_FORMS', resp.content.decode('utf8'))

    def test_update(self):
        resp = self.ads_manager_city35_client.post(
            f'/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}',
            {
                'number': self.ads.id,
                'owner_name': 'Jean-Jacques Goldman',
                'adsuser_set-TOTAL_FORMS': 10,
                'adsuser_set-INITIAL_FORMS': 0,
                'adsuser_set-MIN_NUM_FORMS': 0,
                'adsuser_set-MAX_NUM_FORMS': 10,

                'adslegalfile_set-TOTAL_FORMS': 10,
                'adslegalfile_set-INITIAL_FORMS': 0,
                'adslegalfile_set-MIN_NUM_FORMS': 0,
                'adslegalfile_set-MAX_NUM_FORMS': 10,
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, f'/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}')
        self.ads.refresh_from_db()
        self.assertEqual(self.ads.owner_name, 'Jean-Jacques Goldman')

    def test_update_duplicate(self):
        """Update ADS with the id of another ADS."""
        other_ads = ADS.objects.create(number='xxx', ads_manager=self.ads_manager_city35)
        resp = self.ads_manager_city35_client.post(
            f'/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}',
            {
                'number': other_ads.number,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Une ADS avec ce numéro existe déjà', resp.content.decode('utf8'))

    def test_update_ads_user(self):
        """If all the fields of a ADS user are empty, the entry should be
        removed."""
        ads_user = ADSUser.objects.create(
            ads=self.ads,
            status='autre',
            name='Paul',
            siret='12312312312312'
        )

        resp = self.ads_manager_city35_client.post(
            f'/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}',
            {
                'number': self.ads.id,
                'adsuser_set-TOTAL_FORMS': 10,
                'adsuser_set-INITIAL_FORMS': 1,
                'adsuser_set-MIN_NUM_FORMS': 0,
                'adsuser_set-MAX_NUM_FORMS': 10,
                'adsuser_set-0-id': ads_user.id,
                'adsuser_set-0-status': '',
                'adsuser_set-0-name': 'Henri',
                'adsuser_set-0-siret': '',

                'adslegalfile_set-TOTAL_FORMS': 10,
                'adslegalfile_set-INITIAL_FORMS': 0,
                'adslegalfile_set-MIN_NUM_FORMS': 0,
                'adslegalfile_set-MAX_NUM_FORMS': 10,
            },
        )

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(ADSUser.objects.count(), 1)
        self.assertEqual(ADSUser.objects.get().name, 'Henri')

    def test_update_ads_legal_file(self):
        legal_file = ADSLegalFile.objects.create(
            ads=self.ads,
            file=SimpleUploadedFile('file.pdf', b'Content')
        )
        new_upload = SimpleUploadedFile('newfile.pdf', b'New content')
        resp = self.ads_manager_city35_client.post(
            f'/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}',
            {
                'number': self.ads.id,
                'adsuser_set-TOTAL_FORMS': 10,
                'adsuser_set-INITIAL_FORMS': 0,
                'adsuser_set-MIN_NUM_FORMS': 0,
                'adsuser_set-MAX_NUM_FORMS': 10,

                'adslegalfile_set-TOTAL_FORMS': 10,
                'adslegalfile_set-INITIAL_FORMS': 1,
                'adslegalfile_set-MIN_NUM_FORMS': 0,
                'adslegalfile_set-MAX_NUM_FORMS': 10,
                'adslegalfile_set-0-id': legal_file.id,
                'adslegalfile_set-0-file': new_upload,
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(ADSLegalFile.objects.count(), 1)
        self.assertEqual(
            ADSLegalFile.objects.get().file.read(),
            b'New content'
        )

    def test_remove_ads_user(self):
        """If all the fields of a ADS user are empty, the entry should be
        removed."""
        ads_user = ADSUser.objects.create(
            ads=self.ads,
            status='autre',
            name='Paul',
            siret='12312312312312'
        )

        resp = self.ads_manager_city35_client.post(
            f'/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}',
            {
                'number': self.ads.id,
                'adsuser_set-TOTAL_FORMS': 10,
                'adsuser_set-INITIAL_FORMS': 1,
                'adsuser_set-MIN_NUM_FORMS': 0,
                'adsuser_set-MAX_NUM_FORMS': 10,
                'adsuser_set-0-id': ads_user.id,
                'adsuser_set-0-status': '',
                'adsuser_set-0-name': '',
                'adsuser_set-0-siret': '',
                'adsuser_set-0-license-number': '',

                'adslegalfile_set-TOTAL_FORMS': 10,
                'adslegalfile_set-INITIAL_FORMS': 0,
                'adslegalfile_set-MIN_NUM_FORMS': 0,
                'adslegalfile_set-MAX_NUM_FORMS': 10,
            },
        )

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(ADSUser.objects.count(), 0)

    def test_update_epci_commune(self):
        # ADSManager related to the first EPCI in database
        epci_ads_manager = EPCI.objects.filter(departement='01')[0].ads_managers.get()
        epci_ads = ADS.objects.create(number='12346', ads_manager=epci_ads_manager)

        # Error, the commune doesn't belong to the same departement than the EPCI
        invalid_commune = Commune.objects.filter(~Q(departement='01')).first()
        resp = self.admin_client.post(
            f'/gestion/{epci_ads_manager.id}/ads/{epci_ads.id}',
            {
                'number': epci_ads.id,
                'epci_commune': invalid_commune.id,

                'adsuser_set-TOTAL_FORMS': 10,
                'adsuser_set-INITIAL_FORMS': 0,
                'adsuser_set-MIN_NUM_FORMS': 0,
                'adsuser_set-MAX_NUM_FORMS': 10,

                'adslegalfile_set-TOTAL_FORMS': 10,
                'adslegalfile_set-INITIAL_FORMS': 0,
                'adslegalfile_set-MIN_NUM_FORMS': 0,
                'adslegalfile_set-MAX_NUM_FORMS': 10,
            }
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Ce choix ne fait pas partie de ceux disponibles', resp.content.decode('utf8'))

        valid_commune = Commune.objects.filter(departement='01').first()
        resp = self.admin_client.post(
            f'/gestion/{epci_ads_manager.id}/ads/{epci_ads.id}',
            {
                'number': epci_ads.id,
                'epci_commune': valid_commune.id,

                'adsuser_set-TOTAL_FORMS': 10,
                'adsuser_set-INITIAL_FORMS': 0,
                'adsuser_set-MIN_NUM_FORMS': 0,
                'adsuser_set-MAX_NUM_FORMS': 10,

                'adslegalfile_set-TOTAL_FORMS': 10,
                'adslegalfile_set-INITIAL_FORMS': 0,
                'adslegalfile_set-MIN_NUM_FORMS': 0,
                'adslegalfile_set-MAX_NUM_FORMS': 10,
            }
        )
        self.assertEqual(resp.status_code, 302)

        epci_ads.refresh_from_db()
        self.assertEqual(epci_ads.epci_commune, valid_commune)

    def test_create_ads_user_invalid_siret(self):
        resp = self.ads_manager_city35_client.post(
            f'/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}',
            {
                'number': self.ads.id,
                'adsuser_set-TOTAL_FORMS': 10,
                'adsuser_set-INITIAL_FORMS': 1,
                'adsuser_set-MIN_NUM_FORMS': 0,
                'adsuser_set-MAX_NUM_FORMS': 10,
                'adsuser_set-0-id': '',
                'adsuser_set-0-status': '',
                'adsuser_set-0-name': '',
                'adsuser_set-0-siret': '1234',
                'adsuser_set-0-license_number': '',

                'adslegalfile_set-TOTAL_FORMS': 10,
                'adslegalfile_set-INITIAL_FORMS': 0,
                'adslegalfile_set-MIN_NUM_FORMS': 0,
                'adslegalfile_set-MAX_NUM_FORMS': 10,
            },
        )
        self.assertEqual(resp.status_code, 200)

        # Make sure the message raised by validate_siret is in the
        # response.
        try:
            validate_siret('xxx')
        except ValidationError as exc:
            self.assertIn(exc.message, resp.content.decode('utf8'))

        self.assertEqual(ADSUser.objects.count(), 0)


class TestADSDeleteView(ClientTestCase):
    def setUp(self):
        super().setUp()
        self.ads = ADS.objects.create(id='12346', ads_manager=self.ads_manager_city35)

    def test_permissions(self):
        for client_name, client, expected_status in (
            ('anonymous', self.anonymous_client, 302),
            ('auth', self.auth_client, 404),
            ('ads_manager 35', self.ads_manager_city35_client, 200),
            ('ads_manager_admin 35', self.ads_manager_administrator_35_client, 200),
        ):
            with self.subTest(client_name=client_name, expected_status=expected_status):
                resp = client.get(f'/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}/delete')
                self.assertEqual(resp.status_code, expected_status)

    def test_get_404(self):
        resp = self.ads_manager_city35_client.get(f'/gestion/{self.ads_manager_city35.id}/ads/999/delete')
        self.assertEqual(resp.status_code, 404)

    def test_delete(self):
        resp = self.ads_manager_city35_client.post(
            f'/gestion/{self.ads_manager_city35.id}/ads/{self.ads.id}/delete',
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, f'/gestion/{self.ads_manager_city35.id}/')
        self.assertRaises(ADS.DoesNotExist, self.ads.refresh_from_db)


class TestADSCreateView(ClientTestCase):
    def test_permissions(self):
        for client_name, client, expected_status in (
            ('anonymous', self.anonymous_client, 302),
            ('auth', self.auth_client, 404),
            ('ads_manager 35', self.ads_manager_city35_client, 200),
            ('ads_manager_admin 35', self.ads_manager_administrator_35_client, 200),
        ):
            with self.subTest(client_name=client_name, expected_status=expected_status):
                resp = client.get(f'/gestion/{self.ads_manager_city35.id}/ads/')
                self.assertEqual(resp.status_code, expected_status)

    def test_create(self):
        resp = self.ads_manager_city35_client.post(
            f'/gestion/{self.ads_manager_city35.id}/ads/',
            {
                'number': 'abcdef',
                'adsuser_set-TOTAL_FORMS': 10,
                'adsuser_set-INITIAL_FORMS': 0,
                'adsuser_set-MIN_NUM_FORMS': 0,
                'adsuser_set-MAX_NUM_FORMS': 10,

                'adslegalfile_set-TOTAL_FORMS': 10,
                'adslegalfile_set-INITIAL_FORMS': 0,
                'adslegalfile_set-MIN_NUM_FORMS': 0,
                'adslegalfile_set-MAX_NUM_FORMS': 10,
            }
        )
        self.assertEqual(resp.status_code, 302)
        new_ads = ADS.objects.order_by('-id')[0]
        self.assertEqual(resp.url, f'/gestion/{self.ads_manager_city35.id}/ads/{new_ads.id}')

    def test_create_duplicate(self):
        """Attempt to create ads with already-existing id."""
        ADS.objects.create(number='123', ads_manager=self.ads_manager_city35)

        resp = self.ads_manager_city35_client.post(
            f'/gestion/{self.ads_manager_city35.id}/ads/',
            {
                'number': '123',
                'adsuser_set-TOTAL_FORMS': 10,
                'adsuser_set-INITIAL_FORMS': 0,
                'adsuser_set-MIN_NUM_FORMS': 0,
                'adsuser_set-MAX_NUM_FORMS': 10,

                'adslegalfile_set-TOTAL_FORMS': 10,
                'adslegalfile_set-INITIAL_FORMS': 0,
                'adslegalfile_set-MIN_NUM_FORMS': 0,
                'adslegalfile_set-MAX_NUM_FORMS': 10,
            }
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Une ADS avec ce numéro existe déjà', resp.content.decode('utf8'))

    def test_create_with_ads_user(self):
        resp = self.ads_manager_city35_client.post(
            f'/gestion/{self.ads_manager_city35.id}/ads/',
            {
                'number': 'abcdef',
                'adsuser_set-TOTAL_FORMS': 10,
                'adsuser_set-INITIAL_FORMS': 0,
                'adsuser_set-MIN_NUM_FORMS': 0,
                'adsuser_set-MAX_NUM_FORMS': 10,
                'adsuser_set-0-status': 'autre',
                'adsuser_set-0-name': 'Paul',
                'adsuser_set-0-siret': '12312312312312',

                'adslegalfile_set-TOTAL_FORMS': 10,
                'adslegalfile_set-INITIAL_FORMS': 0,
                'adslegalfile_set-MIN_NUM_FORMS': 0,
                'adslegalfile_set-MAX_NUM_FORMS': 10,
            }
        )
        self.assertEqual(resp.status_code, 302)
        new_ads = ADS.objects.order_by('-id')[0]
        self.assertEqual(resp.url, f'/gestion/{self.ads_manager_city35.id}/ads/{new_ads.id}')

        self.assertEqual(ADSUser.objects.count(), 1)
        new_ads_user = ADSUser.objects.get()
        self.assertEqual(new_ads_user.status, 'autre')
        self.assertEqual(new_ads_user.name, 'Paul')
        self.assertEqual(new_ads_user.siret, '12312312312312')

    def test_create_with_legal_files(self):
        legal_file1 = SimpleUploadedFile(
            name='myfile.pdf',
            content=b'First file',
            content_type='application/pdf'
        )
        legal_file2 = SimpleUploadedFile(
            name='myfile2.pdf',
            content=b'Second file',
            content_type='application/pdf'
        )

        resp = self.ads_manager_city35_client.post(
            f'/gestion/{self.ads_manager_city35.id}/ads/',
            {
                'number': 'abcdef',
                'adsuser_set-TOTAL_FORMS': 10,
                'adsuser_set-INITIAL_FORMS': 0,
                'adsuser_set-MIN_NUM_FORMS': 0,
                'adsuser_set-MAX_NUM_FORMS': 10,

                'adslegalfile_set-TOTAL_FORMS': 10,
                'adslegalfile_set-INITIAL_FORMS': 0,
                'adslegalfile_set-MIN_NUM_FORMS': 0,
                'adslegalfile_set-MAX_NUM_FORMS': 10,
                'adslegalfile_set-0-file': legal_file1,
                'adslegalfile_set-1-file': legal_file2,
            }
        )
        self.assertEqual(resp.status_code, 302)
        new_ads = ADS.objects.order_by('-id')[0]
        self.assertEqual(resp.url, f'/gestion/{self.ads_manager_city35.id}/ads/{new_ads.id}')

        self.assertEqual(ADSLegalFile.objects.count(), 2)
        legal_files = ADSLegalFile.objects.order_by('id')

        self.assertEqual(legal_files[0].file.read(), b'First file')
        self.assertEqual(legal_files[1].file.read(), b'Second file')


class TestCSVExport(ClientTestCase):
    def test_permissions(self):
        for client_name, client, expected_status in (
            ('admin', self.admin_client, 200),
            ('anonymous', self.anonymous_client, 302),
            ('auth', self.auth_client, 404),
            ('ads_manager 35', self.ads_manager_city35_client, 404),
            ('ads_manager_admin 35', self.ads_manager_administrator_35_client, 200),
        ):
            with self.subTest(client_name=client_name, expected_status=expected_status):
                resp = client.get(f'/prefectures/{self.ads_manager_administrator_35.prefecture.id}/export')
                self.assertEqual(resp.status_code, expected_status)

    def test_get_404(self):
        resp = self.ads_manager_administrator_35_client.get('/prefectures/9999/export')
        self.assertEqual(resp.status_code, 404)

    def test_export(self):
        ADS.objects.create(number='1', ads_manager=self.ads_manager_city35, accepted_cpam=True)
        ADS.objects.create(number='2', ads_manager=self.ads_manager_city35)
        ADS.objects.create(number='3', ads_manager=self.ads_manager_city35)

        resp = self.ads_manager_administrator_35_client.get(
            f'/prefectures/{self.ads_manager_administrator_35.prefecture.id}/export'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers['Content-Type'], 'text/csv')

        # Header + 2 ADS
        self.assertEqual(len(resp.content.splitlines()), 4)


class TestDashboardsViews(ClientTestCase):
    """Test DashboardsView and DashboardsDetailView"""

    def setUp(self):
        super().setUp()
        request = RequestFactory().get('/dashboards')
        self.dashboards_view = DashboardsView()
        self.dashboards_view.setup(request)

        request = RequestFactory().get(f'/dashboards/{self.ads_manager_administrator_35.id}')
        self.dashboards_detail_view = DashboardsDetailView(object=self.ads_manager_administrator_35)
        self.dashboards_detail_view.setup(request)

    def test_permissions(self):
        for client_name, client, expected_status in (
            ('anonymous', self.anonymous_client, 302),
            ('auth', self.auth_client, 302),
            ('ads_manager 35', self.ads_manager_city35_client, 302),
            ('ads_manager_admin 35', self.ads_manager_administrator_35_client, 302),
            ('admin', self.admin_client, 200),
        ):
            with self.subTest(client_name=client_name, expected_status=expected_status):
                resp = client.get('/dashboards')
                self.assertEqual(resp.status_code, expected_status)

                resp = client.get(f'/dashboards/{self.ads_manager_administrator_35.id}/')
                self.assertEqual(resp.status_code, expected_status)

    def test_stats_default(self):
        # The base class ClientTestCase creates ads_manager_administrator for
        # departement 35, and configures an ADSManager for the city fo Melesse.
        self.assertEqual([{
            'obj': self.ads_manager_administrator_35,
            'ads': {},
            'users': {
                'now': 1,
            }
        }], self.dashboards_view.get_stats())

        self.assertEqual([{
            'obj': self.ads_manager_city35,
            'ads': {},
            'users': {
                'now': 1,
            }
        }], self.dashboards_detail_view.get_stats())

    def test_stats_for_several_ads(self):
        # Create several ADS for the city of Melesse
        now = timezone.now()
        for (idx, creation_date) in enumerate([
            now - timedelta(days=365 * 2),  # 2 years old ADS
            now - timedelta(days=300),      # > 6 && < 12 months old
            now - timedelta(days=120),      # > 3 && < 6 months old
            now - timedelta(days=1),        # yesterday
        ]):
            ads = ADS.objects.create(number=str(idx), ads_manager=self.ads_manager_city35)
            ads.creation_date = creation_date
            ads.save()

        self.assertEqual([{
            'obj': self.ads_manager_administrator_35,
            'ads': {
                'now': 4,
                '3_months': 3,
                '6_months': 2,
                '12_months': 1,
            },
            'users': {
                'now': 1,
            }
        }], self.dashboards_view.get_stats())

        self.assertEqual([{
            'obj': self.ads_manager_city35,
            'ads': {
                'now': 4,
                '3_months': 3,
                '6_months': 2,
                '12_months': 1,
            },
            'users': {
                'now': 1,
            }
        }], self.dashboards_detail_view.get_stats())

    def test_stats_for_several_ads_managers(self):
        now = timezone.now()
        # Give administration permissions for several users to Melesse.
        for creation_date in [
            now - timedelta(days=365 * 2),  # 2 years old ADS
            now - timedelta(days=300),      # > 6 && < 12 months old
            now - timedelta(days=120),      # > 3 && < 6 months old
            now - timedelta(days=1),        # yesterday
        ]:
            user = self.create_user().obj
            ads_manager_request = ADSManagerRequest.objects.create(
                user=user,
                ads_manager=self.ads_manager_city35,
                accepted=True,
            )
            ads_manager_request.created_at = creation_date
            ads_manager_request.save()

        self.assertEqual([{
            'obj': self.ads_manager_administrator_35,
            'ads': {},
            'users': {
                'now': 5,
                '3_months': 3,
                '6_months': 2,
                '12_months': 1,
            }
        }], self.dashboards_view.get_stats())

        self.assertEqual([{
            'obj': self.ads_manager_city35,
            'ads': {},
            'users': {
                'now': 5,
                '3_months': 3,
                '6_months': 2,
                '12_months': 1,
            }
        }], self.dashboards_detail_view.get_stats())


class TestFAQView(ClientTestCase):
    def test_get(self):
        resp = self.client.get('/faq')
        self.assertEqual(resp.status_code, 200)
