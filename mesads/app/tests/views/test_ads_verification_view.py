from datetime import date
from http import HTTPStatus

import pytest
from dateutil.relativedelta import relativedelta
from django.urls import reverse

from mesads.app.models import ADS, ADSUpdateLog, ADSUser

pytestmark = pytest.mark.django_db


def test_get_verification(user, client_logged, commune, ads_manager_request):
    ads_manager_request(user)
    ads = ADS.objects.create(
        number="12346",
        ads_manager=commune,
        ads_in_use=True,
        creation_date=date(2020, 1, 1),
        owner_name="Nom Prénom",
        owner_siret="1234567890123",
        immatriculation_plate="GJKDFH01",
        vehicle_compatible_pmr=True,
        eco_vehicle=False,
    )
    ADSUser.objects.create(
        ads=ads, status=ADSUser.TITULAIRE_EXPLOITANT, license_number="BJKQK45"
    )
    ADSUpdateLog.create_for_ads(ads, user)

    response = client_logged.get(
        reverse(
            "app.ads.verification", kwargs={"manager_id": commune.id, "ads_id": ads.id}
        )
    )
    assert response.status_code == HTTPStatus.OK
    assert response.context["ads"] == ads
    assert response.context["ads_manager"] == commune
    assert "pages/ads_register/ads_verification.html" in [
        t.name for t in response.templates
    ]


def test_post_confirm_verification(user, client_logged, commune, ads_manager_request):
    ads_manager_request(user)
    ads = ADS.objects.create(
        number="12346",
        ads_manager=commune,
        ads_in_use=True,
        ads_creation_date=date(2020, 1, 1),
        owner_name="Nom Prénom",
        owner_siret="1234567890123",
        immatriculation_plate="GJKDFH01",
        vehicle_compatible_pmr=True,
        eco_vehicle=False,
    )
    ADSUser.objects.create(
        ads=ads, status=ADSUser.TITULAIRE_EXPLOITANT, license_number="BJKQK45"
    )
    ADSUpdateLog.create_for_ads(ads, user)
    update_log = ads.ads_update_logs.last()
    update_log.update_at = update_log.update_at - relativedelta(years=1)

    assert update_log.is_outdated()

    response = client_logged.post(
        reverse(
            "app.ads.verification-confirmation",
            kwargs={"manager_id": commune.id, "ads_id": ads.id},
        )
    )
    ads.refresh_from_db()
    last_log = ads.ads_update_logs.last()
    assert last_log != update_log
    assert not last_log.is_outdated()
    assert last_log.debug_missing_fields == "[]"
    assert response.status_code == HTTPStatus.FOUND
    assert response.url == reverse(
        "app.ads-manager.detail", kwargs={"manager_id": commune.id}
    )
