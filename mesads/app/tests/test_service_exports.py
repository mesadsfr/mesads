import pytest

from mesads.app.services.export import get_prefectures_data_listes_attente

from .factories import (
    ADSManagerAdministratorFactory,
    ADSManagerFactory,
    InscriptionListeAttenteFactory,
)

pytestmark = pytest.mark.django_db


def test_get_export_data_liste_attente():
    administrator = ADSManagerAdministratorFactory()
    prefecture = ADSManagerFactory(
        administrator=administrator, for_object=administrator.prefecture
    )
    commune = ADSManagerFactory(administrator=administrator, for_commune=True)
    epci = ADSManagerFactory(administrator=administrator, for_epci=True)

    InscriptionListeAttenteFactory(ads_manager=prefecture)
    InscriptionListeAttenteFactory(ads_manager=commune)
    InscriptionListeAttenteFactory(ads_manager=epci)

    headers, rows = get_prefectures_data_listes_attente()

    assert headers == [
        "Département",
        "Nombre de communes",
        "Nombre de communes avec une liste d'attente publique ou non",
        "Nombre d'EPCI avec une liste d'attente publique ou non",
        "Préfecture avec une liste d'attente publique ou non",
        "Nombre d'aéroports avec une liste d'attente publique ou non",
        "Nombre d'inscrits sur des communes",
        "Nombre d'inscrits sur des EPCI",
        "Nombre d'inscrits sur la préfecture",
        "Nombre d'inscrits sur des aéroports",
    ]
    assert len(rows) == 1
    assert rows[0] == (administrator.prefecture.libelle, 1, 1, 1, 1, 0, 1, 1, 1, 0)
