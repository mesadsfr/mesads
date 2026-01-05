import datetime
import http

from django.urls import reverse

from mesads.app.models import ADS, ADSManager, ADSManagerAdministrator, ADSUpdateLog
from mesads.fradm.models import Prefecture
from mesads.users.unittest import ClientTestCase


class TestAdminStatistiquesView(ClientTestCase):
    """Make sure password reset sends HTML email and the contact address is
    present in the email."""

    def init_data(self):
        prefecture = Prefecture.objects.create(numero="01", libelle="Ain")
        ads_manager_administrator = ADSManagerAdministrator.objects.create(
            prefecture=prefecture
        )
        ads_manager = ADSManager.objects.create(
            content_object=prefecture, administrator=ads_manager_administrator
        )
        ads_manager.save()

        ads_date = datetime.date.today() - datetime.timedelta(days=200)
        ads_1 = ADS.objects.create(
            ads_manager=ads_manager,
            number="1",
            ads_creation_date=ads_date,
            ads_in_use=True,
            ads_renew_date=ads_date,
            accepted_cpam=True,
            immatriculation_plate="FRDHS01",
            vehicle_compatible_pmr=True,
            eco_vehicle=True,
            owner_name="John Doe",
            owner_siret="12345678901234",
            owner_phone="0606060606",
            owner_email="test@test.com",
        )
        ADSUpdateLog.objects.create(
            ads=ads_1,
            user=self.auth_user,
            serialized="",
            is_complete=True,
            debug_missing_fields="[]",
        )
        ads_2 = ADS.objects.create(
            ads_manager=ads_manager,
            number="2",
            ads_creation_date=ads_date,
            ads_in_use=True,
            ads_renew_date=ads_date,
            accepted_cpam=True,
            immatriculation_plate="FRDHS01",
            vehicle_compatible_pmr=True,
            eco_vehicle=True,
            owner_name="Jane Doe",
            owner_siret="12345678901234",
            owner_phone="0606060606",
            owner_email="test@test.com",
        )
        ADSUpdateLog.objects.create(
            ads=ads_2,
            user=self.auth_user,
            serialized="",
            is_complete=False,
            debug_missing_fields="[]",
        )

    def test_get_as_normal_user(self):
        response = self.auth_client.get(reverse("admin-statistiques"))
        self.assertEqual(response.status_code, http.HTTPStatus.FOUND)

    def test_get_as_anonymous_user(self):
        response = self.anonymous_client.get(reverse("admin-statistiques"))
        self.assertEqual(response.status_code, http.HTTPStatus.FOUND)

    def test_get_as_admin(self):
        self.init_data()
        response = self.admin_client.get(reverse("admin-statistiques"))
        assert response.context["pourcentage_ads_valide_et_complete"] == 50.0
        assert response.context["nombre_creation_modification_ads"] == 2
        assert response.context["nombre_connexions"] == 2
        self.assertEqual(response.status_code, http.HTTPStatus.OK)

    def test_get_as_admin_with_params(self):
        self.init_data()
        response = self.admin_client.get(
            f"{reverse('admin-statistiques')}?start_date=2025-08-01&end_date=2025-08-31"
        )
        assert response.context["pourcentage_ads_valide_et_complete"] == 50.0
        assert response.context["nombre_creation_modification_ads"] == 0
        assert response.context["nombre_connexions"] == 0
        self.assertEqual(response.status_code, http.HTTPStatus.OK)
