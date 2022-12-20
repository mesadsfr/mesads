from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework.test import APIClient

from mesads.app.models import ADS, ADSUpdateFile
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


class TestStatsGeoJSONPerPrefecture(ClientTestCase):
    # ClientTestCase initializes PREFECTURES with a limited subset of prefectures. The endpoint requires all prefectures.
    PREFECTURES = (
        ('01', "Ain"),
        ('02', "Aisne"),
        ('03', "Allier"),
        ('04', "Alpes-de-Haute-Provence"),
        ('05', "Hautes-Alpes"),
        ('06', "Alpes-Maritimes"),
        ('07', "Ardèche"),
        ('08', "Ardennes"),
        ('09', "Ariège"),
        ('10', "Aube"),
        ('11', "Aude"),
        ('12', "Aveyron"),
        ('13', "Bouches-du-Rhône"),
        ('14', "Calvados"),
        ('15', "Cantal"),
        ('16', "Charente"),
        ('17', "Charente-Maritime"),
        ('18', "Cher"),
        ('19', "Corrèze"),
        ('21', "Côte-d'Or"),
        ('22', "Côtes-d'Armor"),
        ('23', "Creuse"),
        ('24', "Dordogne"),
        ('25', "Doubs"),
        ('26', "Drôme"),
        ('27', "Eure"),
        ('28', "Eure-et-Loir"),
        ('29', "Finistère"),
        ('2A', "Corse-du-Sud"),
        ('2B', "Haute-Corse"),
        ('30', "Gard"),
        ('31', "Haute-Garonne"),
        ('32', "Gers"),
        ('33', "Gironde"),
        ('34', "Hérault"),
        ('35', "Ille-et-Vilaine"),
        ('36', "Indre"),
        ('37', "Indre-et-Loire"),
        ('38', "Isère"),
        ('39', "Jura"),
        ('40', "Landes"),
        ('41', "Loir-et-Cher"),
        ('42', "Loire"),
        ('43', "Haute-Loire"),
        ('44', "Loire-Atlantique"),
        ('45', "Loiret"),
        ('46', "Lot"),
        ('47', "Lot-et-Garonne"),
        ('48', "Lozère"),
        ('49', "Maine-et-Loire"),
        ('50', "Manche"),
        ('51', "Marne"),
        ('52', "Haute-Marne"),
        ('53', "Mayenne"),
        ('54', "Meurthe-et-Moselle"),
        ('55', "Meuse"),
        ('56', "Morbihan"),
        ('57', "Moselle"),
        ('58', "Nièvre"),
        ('59', "Nord"),
        ('60', "Oise"),
        ('61', "Orne"),
        ('62', "Pas-de-Calais"),
        ('63', "Puy-de-Dôme"),
        ('64', "Pyrénées-Atlantiques"),
        ('65', "Hautes-Pyrénées"),
        ('66', "Pyrénées-Orientales"),
        ('67', "Bas-Rhin"),
        ('68', "Haut-Rhin"),
        ('69', "Rhône"),
        ('70', "Haute-Saône"),
        ('71', "Saône-et-Loire"),
        ('72', "Sarthe"),
        ('73', "Savoie"),
        ('74', "Haute-Savoie"),
        ('75', "Préfecture de Police de Paris"),
        ('76', "Seine-Maritime"),
        ('77', "Seine-et-Marne"),
        ('78', "Yvelines"),
        ('79', "Deux-Sèvres"),
        ('80', "Somme"),
        ('81', "Tarn"),
        ('82', "Tarn-et-Garonne"),
        ('83', "Var"),
        ('84', "Vaucluse"),
        ('85', "Vendée"),
        ('86', "Vienne"),
        ('87', "Haute-Vienne"),
        ('88', "Vosges"),
        ('89', "Yonne"),
        ('90', "Territoire de Belfort"),
        ('91', "Essonne"),
        ('92', "Hauts-de-Seine"),
        ('93', "Seine-Saint-Denis"),
        ('94', "Val-de-Marne"),
        ('95', "Val-d'Oise"),
        ('971', "Guadeloupe"),
        ('972', "Martinique"),
        ('973', "Guyane"),
        ('974', "La Réunion"),
        ('976', "Mayotte"),
    )

    def test_get_unauthorized(self):
        client = APIClient()
        resp = client.get('/api/stats/geojson/per-prefecture/')
        self.assertEqual(resp.status_code, 401)

    def test_get(self):
        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        # Create 3 ADS in departement 35
        ADS.objects.create(number='1', ads_manager=self.ads_manager_city35)
        ADS.objects.create(number='2', ads_manager=self.ads_manager_city35)
        ADS.objects.create(number='3', ads_manager=self.ads_manager_city35)

        resp = client.get('/api/stats/geojson/per-prefecture/')
        self.assertEqual(resp.status_code, 200)

        for feature in resp.json()['features']:
            if feature['properties']['code_insee'] == '35':
                self.assertEqual(feature['properties']['ads_count'], 3)
            else:
                self.assertEqual(feature['properties']['ads_count'], 0)
