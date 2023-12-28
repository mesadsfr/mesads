import datetime

from mesads.fradm.unittest import ClientTestCase as BaseClientTestCase

from mesads.vehicules_relais.models import Proprietaire, Vehicule
from mesads.fradm.models import Prefecture


class ClientTestCase(BaseClientTestCase):
    def setUp(self):
        """Create a proprietaire object, and register vehicules to it."""
        super().setUp()

        self.proprietaire_client, self.proprietaire_user = self.create_client()

        self.proprietaire = Proprietaire.objects.create(nom="Propriétaire")
        self.proprietaire.users.set([self.proprietaire_user])

        ille_et_vilaine = Prefecture.objects.filter(numero="35").get()
        gironde = Prefecture.objects.filter(numero="33").get()

        # Assign three vehicules to the proprietaire in Ille-et-Vilaine.
        Vehicule.objects.create(
            proprietaire=self.proprietaire,
            departement=ille_et_vilaine,
            immatriculation="123-456-789",
            modele="Peugeot 308",
            motorisation="essence",
            date_mise_circulation=datetime.date(2019, 1, 1),
            nombre_places=4,
            pmr=False,
            commune_localisation=None,
        )
        Vehicule.objects.create(
            proprietaire=self.proprietaire,
            departement=ille_et_vilaine,
            immatriculation="666-666-666",
            modele="Range rover",
            motorisation="essence",
            date_mise_circulation=datetime.date(2020, 5, 1),
            nombre_places=4,
            pmr=True,
            commune_localisation=None,
        )
        Vehicule.objects.create(
            proprietaire=self.proprietaire,
            departement=ille_et_vilaine,
            immatriculation="AAAA-AAAA",
            modele="Tesla modele S",
            motorisation="electrique",
            date_mise_circulation=datetime.date(2023, 5, 1),
            nombre_places=4,
            pmr=False,
            commune_localisation=None,
        )
        # Assign one vehicule to the proprietaire in Gironde
        Vehicule.objects.create(
            proprietaire=self.proprietaire,
            departement=gironde,
            immatriculation="BBBB-BBBB",
            modele="Renault Clio",
            motorisation="hybride",
            date_mise_circulation=datetime.date(2023, 5, 1),
            nombre_places=4,
            pmr=False,
            commune_localisation=None,
        )

        # Assign one vehicule to another proprietaire in Ille-et-Vilaine
        other_proprietaire = Proprietaire.objects.create(nom="Un autre propriétaire")
        Vehicule.objects.create(
            proprietaire=other_proprietaire,
            departement=ille_et_vilaine,
            immatriculation="CCC-CCC-CCC",
            modele="Tesla modele S",
            motorisation="electrique",
            date_mise_circulation=datetime.date(2025, 5, 1),
            nombre_places=4,
            pmr=False,
            commune_localisation=None,
        )
