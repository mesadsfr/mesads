from django.core.exceptions import ValidationError

from mesads.fradm.models import Prefecture
from mesads.vehicules_relais.models import Vehicule

from .unittest import ClientTestCase


class TestVehicules(ClientTestCase):
    def test_main_features(self):
        departement = Prefecture.objects.first()
        vehicule = Vehicule.objects.create(
            proprietaire=self.proprietaire,
            departement=departement,
        )
        for motorisation, motorisation_as_text in (
            ("electrique", "Véhicule électrique"),
            ("hybride", "Véhicule hybride"),
            ("hybride_rechargeable", "Véhicule hybride rechargeable"),
        ):
            vehicule = Vehicule.objects.create(
                proprietaire=self.proprietaire,
                departement=departement,
                motorisation=motorisation,
                pmr=True,
            )
            features = vehicule.main_features()
            self.assertEqual(features, [motorisation_as_text, "Accès PMR"])

    def test_clean(self):
        departement = Prefecture.objects.first()
        other_departement = Prefecture.objects.create(
            numero="94", libelle="Val de Marne"
        )
        vehicule = Vehicule.objects.create(
            proprietaire=self.proprietaire,
            departement=departement,
        )
        vehicule.departement = other_departement
        self.assertRaises(ValidationError, Vehicule.clean, vehicule)
