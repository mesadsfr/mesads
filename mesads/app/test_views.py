from django.core import mail

from mesads.fradm.models import EPCI, Prefecture

from .models import ADS, ADSManagerRequest, ADSUser
from .unittest import ClientTestCase


class TestHomepageView(ClientTestCase):
    def test_redirection(self):
        for client_name, client, expected_status, redirect_url in (
            ('anonymous', self.anonymous_client, 302, '/auth/login/?next=/'),
            ('auth', self.auth_client, 302, '/gestion'),
            ('ads_manager 35', self.ads_manager_city35_client, 302, '/gestion'),
            ('ads_manager_admin 35', self.ads_manager_administrator_35_client, 302, '/admin_gestion'),
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
        self.assertNotIn('error', resp.content.decode('utf8'))
        self.assertEqual(ADSManagerRequest.objects.count(), self.initial_ads_managers_count + 1)

        # Make sure django message is in the next request
        resp = self.auth_client.get('/gestion')
        self.assertEqual(len(resp.context['messages']), 1)

        # If there is a ADSManagerAdministrator related to the commune, an email is sent for each member.
        # The base class ClientTestCase configures Melesse to be managed by the ADSManagerAdministrator entry of
        # l'Ille-et-Vilaine.
        self.assertEqual(len(mail.outbox), 1)

    def test_create_request_epci(self):
        epci = EPCI.objects.first()
        resp = self.auth_client.post('/gestion', {
            'epci': epci.id
        })
        self.assertNotIn('error', resp.content.decode('utf8'))
        self.assertEqual(ADSManagerRequest.objects.count(), self.initial_ads_managers_count + 1)

        # Make sure django message is in the next request
        resp = self.auth_client.get('/gestion')
        self.assertEqual(len(resp.context['messages']), 1)

    def test_create_request_prefecture(self):
        prefecture = Prefecture.objects.first()
        resp = self.auth_client.post('/gestion', {
            'prefecture': prefecture.id
        })
        self.assertNotIn('error', resp.content.decode('utf8'))
        self.assertEqual(ADSManagerRequest.objects.count(), self.initial_ads_managers_count + 1)

        # Make sure django message is in the next request
        resp = self.auth_client.get('/gestion')
        self.assertEqual(len(resp.context['messages']), 1)


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
                'adsuser_set-INITIAL_FORMS': 2,
                'adsuser_set-MIN_NUM_FORMS': 0,
                'adsuser_set-MAX_NUM_FORMS': 10,
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
            },
        )

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(ADSUser.objects.count(), 1)
        self.assertEqual(ADSUser.objects.get().name, 'Henri')

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
            },
        )

        self.assertEqual(resp.status_code, 302)
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
                'adsuser_set-INITIAL_FORMS': 2,
                'adsuser_set-MIN_NUM_FORMS': 0,
                'adsuser_set-MAX_NUM_FORMS': 10,
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
                'adsuser_set-INITIAL_FORMS': 2,
                'adsuser_set-MIN_NUM_FORMS': 0,
                'adsuser_set-MAX_NUM_FORMS': 10,
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


class TestCSVExport(ClientTestCase):
    def test_permissions(self):
        for client_name, client, expected_status in (
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
