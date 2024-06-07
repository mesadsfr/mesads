from mesads.users.unittest import ClientTestCase as BaseClientTestCase

from .models import Commune, EPCI, Prefecture


class ClientTestCase(BaseClientTestCase):
    COMMUNES = (
        ("01001", "01", "L'Abergement-Clémenciat"),
        ("01008", "01", "Ambutrix"),
        ("13055", "13", "Marseille"),
        ("35173", "35", "Melesse"),
        ("75056", "75", "Paris"),
        ("97616", "976", "Sada"),
        ("97617", "976", "Tsingoni"),
    )

    EPCI = (
        ("200029999", "01", "CC Rives de l'Ain - Pays du Cerdon"),
        ("200040350", "01", "CC Bugey Sud"),
        ("200055655", "95", "CA Roissy Pays de France"),
    )

    PREFECTURES = (
        ("01", "Ain"),
        ("13", "Bouches-du-Rhône"),
        ("33", "Gironde"),
        ("35", "Ille-et-Vilaine"),
        ("73", "Savoie"),
        ("75", "Préfecture de Police de Paris"),
        ("95", "Val-d'Oise"),
        ("976", "Mayotte"),
    )

    def setUp(self):
        """Create some prefectures, EPCI and communes useful for unittests."""
        super().setUp()
        self.create_fixtures()

    def create_fixtures(self):
        """Simulates the commands load_communes, load_epci and load_prefectures."""
        self.fixtures_communes = []
        self.fixtures_epci = []
        self.fixtures_prefectures = []

        for insee, departement, libelle in self.COMMUNES:
            obj = Commune.objects.create(
                insee=insee, departement=departement, libelle=libelle
            )
            self.fixtures_communes.append(obj)

        for siren, departement, name in self.EPCI:
            obj = EPCI.objects.create(siren=siren, departement=departement, name=name)
            self.fixtures_epci.append(obj)

        for numero, libelle in self.PREFECTURES:
            obj = Prefecture.objects.create(numero=numero, libelle=libelle)
            self.fixtures_prefectures.append(obj)
