from django.test import TestCase

from .models import Commune, EPCI, Prefecture


class TestCommune(TestCase):
    def test_type_name(self):
        commune = Commune()
        self.assertEqual(commune.type_name(), "commune")

    def test_text(self):
        commune = Commune(libelle="Anthony")
        self.assertEqual(commune.text(), "Anthony")

    def test_display_text(self):
        commune = Commune(libelle="Anthony")
        self.assertIn("d'", commune.display_text())
        self.assertNotIn("de", commune.display_text())

        commune = Commune(libelle="Bobigny")
        self.assertNotIn("d'", commune.display_text())
        self.assertIn("de", commune.display_text())

    def test_display_fulltext(self):
        commune = Commune(libelle="Anthony")
        self.assertTrue(commune.display_fulltext().startswith("la"))

    def test_str(self):
        commune = Commune(insee="92002", departement="92", libelle="Anthony")
        self.assertIn("Anthony", str(commune))
        self.assertIn("92002", str(commune))
        self.assertIn("92 ", str(commune))


class TestPrefecture(TestCase):
    def test_type_name(self):
        prefecture = Prefecture()
        self.assertEqual(prefecture.type_name(), "préfecture")

    def test_text(self):
        prefecture = Prefecture(libelle="Préfecture de Police de Paris")
        self.assertEqual(prefecture.text(), "Préfecture de Police de Paris")

    def test_display_text(self):
        prefecture = Prefecture(numero="75", libelle="Préfecture de Police de Paris")
        self.assertEqual(prefecture.display_text(), "préfecture de Police de Paris")

        prefecture = Prefecture(numero="35", libelle="Ille-et-Vilaine")
        self.assertEqual(prefecture.display_text(), "préfecture d'Ille-et-Vilaine")

        prefecture = Prefecture(numero="83", libelle="Var")
        self.assertEqual(prefecture.display_text(), "préfecture de Var")

    def test_display_fulltext(self):
        prefecture = Prefecture(numero="75", libelle="Préfecture de Police de Paris")
        self.assertTrue(prefecture.display_fulltext().startswith("la"))

    def test_str(self):
        prefecture = Prefecture(numero="75", libelle="Préfecture de Police de Paris")
        self.assertIn("75", str(prefecture))
        self.assertIn("Préfecture de Police de Paris", str(prefecture))


class TestEPCI(TestCase):
    def test_type_name(self):
        epci = EPCI()
        self.assertEqual(epci.type_name(), "EPCI")

    def test_text(self):
        epci = EPCI(name="CC du Sud")
        self.assertEqual(epci.text(), "CC du Sud")

    def test_display_text(self):
        epci = EPCI(siren="200060473", departement="976", name="CC du Sud")
        self.assertEqual(epci.display_text(), "EPCI CC du Sud")

    def test_display_fulltext(self):
        epci = EPCI(siren="200060473", departement="976", name="CC du Sud")
        self.assertEqual(epci.display_fulltext(), "l'EPCI CC du Sud")

    def test_str(self):
        epci = EPCI(siren="200060473", departement="976", name="CC du Sud")
        self.assertEqual(str(epci), "CC du Sud")
