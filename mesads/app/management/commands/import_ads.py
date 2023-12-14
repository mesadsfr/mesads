import datetime
import functools
import itertools
import re
import string
import sys
from unidecode import unidecode

import openpyxl

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from mesads.app.models import ADS, ADSManager, validate_siret
from mesads.fradm.models import Commune, Prefecture


class Excel:
    """Helper to manipulate an excel file"""

    def __init__(self, header):
        self.header = header
        self.normalized_header = [h.lower() for h in self.header]

    def colnames(self):
        """Return all columns names in order (A, B, C, ..., Z, AA, AB, AC, ...,
        AZ, BA, BB, BC, ..., ZZ, AAA, AAB, ... ZZZ)"""
        return (
            "".join(v)
            for v in itertools.chain(
                itertools.product(string.ascii_uppercase, repeat=1),
                itertools.product(string.ascii_uppercase, repeat=2),
                itertools.product(string.ascii_uppercase, repeat=3),
            )
        )

    def idx_to_colname(self, nth):
        """Return the nth excel column name"""
        return next(itertools.islice(self.colnames(), nth, nth + 1))

    def find_cols(self, colname, exact=False):
        """Return the index of the given column name. If exact=False, the column
        name can be partial, but must be unambiguous."""
        candidates = []
        last_match = None
        for idx, col in enumerate(self.normalized_header):
            # Exact match in one of the lines of the header, or partial match
            if (exact and colname.lower() in col.split("\n")) or (
                not exact and colname.lower() in col
            ):
                candidates.append(idx)
                if last_match and last_match.lower() != col.lower():
                    err_last_match = "\n".join(
                        f"\t{line}" for line in last_match.splitlines()
                    )
                    err_col = "\n".join(f"\t{line}" for line in col.splitlines())

                    raise ValueError(
                        f'La colonne "{colname}" est trouvée plusieurs fois avec des valeurs différentes, par exemple :\n{err_last_match}\net :\n{err_col}. Régler le problème ou ajouter exact=True'
                    )
                last_match = col

        if len(candidates) == 0:
            raise ValueError(f'Colonne "{colname}" inconnue')
        return candidates

    def idx(self, colname, exact=False):
        cols = self.find_cols(colname, exact=exact)
        if len(cols) > 1:
            raise ValueError(
                f"Colonne \"{colname}\" ambiguë ({len(cols)} résultats: {', '.join((self.idx_to_colname(candidate) for candidate in cols))})"
            )
        return cols[0]

    def nidx(self, colname, nth, exact=False):
        """Return the index of the nth column with the given name"""
        cols = self.find_cols(colname, exact=exact)
        return cols[nth]


class ADSImporter:
    COLUMNS = (
        # Col 0: A
        "Numéro du département de la commune",
        # Col 1: B
        "Nom de la commune",
        # Col 2: C
        "Numéro de l'ADS",
        # Col 3: D
        "Date de création de l'ADS\ndate à laquelle l'ADS a été attribuée pour la première fois",
        # Col 4: E
        "Date du dernier renouvellement de l'ADS\nRemplir seulement si l'ADS a été attribuée pour la première fois après le 01/10/2014 : Les ADS créées depuis le 1er octobre 2014 sont valables 5 ans et doivent être renouvelées.",
        # Col 5: F
        "Date d'attribution de l'ADS au titulaire actuel\nLaissez ce champ vide si le titulaire n'a pas changé depuis la création de l'ADS. Ne remplir que si l'ADS a été attribuée pour la première fois avant le 01/10/2014",
        # Col 6: G
        'Véhicule conventionné CPAM ?\nMettre "oui" ou "non". Laissez vide si vous ne savez pas.',
        # Col 7: H
        "Plaque d'immatriculation",
        # Col 8: I
        'Véhicule compatible PMR ?\nMettre "oui" ou "non", laissez vide si vous ne savez pas',
        # Col 9: J
        "Titulaire de l'ADS\nS'il s'agit d'une personne physique, précisez le nom et le prénom du titulaire de l'ADS. S'il s'agit d'une personne morale, indiquez sa raison sociale.",
        # Col 10: K
        "SIRET du titulaire de l'ADS",
        # Col 11: L
        "Téléphone fixe du titulaire de l'ADS",
        # Col 12: M
        "Téléphone mobile du titulaire de l'ADS",
        # Col 13: N
        "Email du titulaire de l'ADS",
        # Col 14: O
        "ADS exploitée par son titulaire ?",
        # Col 15: P
        "Numéro de la carte professionnelle du titulaire\nÀ remplir UNIQUEMENT si l'ADS est exploitée par le titulaire",
        # Col 16: Q
        "Les colonnes suivantes ne doivent être remplies que si l'ADS n'est PAS exploitée par son titulaire\n\nEntrez dans les 4 colonnes à droite les informations du 1er exploitant",
        # Col 17: R
        'Modalité d\'exploitation de l\'ADS\n"Salarié", "Locataire gérant", "Locataire coopérateur", "Titulaire exploitant" ou "Autre"',
        # Col 18: S
        "Nom de l'exploitant de l'ADS",
        # Col 19: T
        "SIRET de l'exploitant de l'ADS",
        # Col 20: U
        "Numéro de la carte professionnelle",
        # Col 21: V
        "Entrez dans les 4 colonnes à droite les informations du 2e exploitant",
        # Col 22: W
        'Modalité d\'exploitation de l\'ADS\n"Salarié", "Locataire gérant", "Locataire coopérateur", "Titulaire exploitant" ou "Autre"',
        # Col 23: X
        "Nom de l'exploitant de l'ADS",
        # Col 24: Y
        "SIRET de l'exploitant de l'ADS",
        # Col 25: Z
        "Numéro de la carte professionnelle",
        # Col 26: AA
        "Entrez dans les 4 colonnes à droite les informations du 3e exploitant",
        # Col 27: AB
        'Modalité d\'exploitation de l\'ADS\n"Salarié", "Locataire gérant", "Locataire coopérateur", "Titulaire exploitant" ou "Autre"',
        # Col 28: AC
        "Nom de l'exploitant de l'ADS",
        # Col 29: AD
        "SIRET de l'exploitant de l'ADS",
        # Col 30: AE
        "Numéro de la carte professionnelle",
        # Col 31: AF
        "Entrez dans les 4 colonnes à droite les informations du 4e exploitant",
        # Col 32: AG
        'Modalité d\'exploitation de l\'ADS\n"Salarié", "Locataire gérant", "Locataire coopérateur", "Titulaire exploitant" ou "Autre"',
        # Col 33: AH
        "Nom de l'exploitant de l'ADS",
        # Col 34: AI
        "SIRET de l'exploitant de l'ADS",
        # Col 35: AJ
        "Numéro de la carte professionnelle",
        # Col 36: AK
        "Entrez dans les 4 colonnes à droite les informations du 5e exploitant",
        # Col 37: AL
        'Modalité d\'exploitation de l\'ADS\n"Salarié", "Locataire gérant", "Locataire coopérateur", "Titulaire exploitant" ou "Autre"',
        # Col 38: AM
        "Nom de l'exploitant de l'ADS",
        # Col 39: AN
        "SIRET de l'exploitant de l'ADS",
        # Col 40: AO
        "Numéro de la carte professionnelle",
        # Col 41: AP
        "Entrez dans les 4 colonnes à droite les informations du 6e exploitant",
        # Col 42: AQ
        'Modalité d\'exploitation de l\'ADS\n"Salarié", "Locataire gérant", "Locataire coopérateur", "Titulaire exploitant" ou "Autre"',
        # Col 43: AR
        "Nom de l'exploitant de l'ADS",
        # Col 44: AS
        "SIRET de l'exploitant de l'ADS",
        # Col 45: AT
        "Numéro de la carte professionnelle",
        # Col 46: AU
        "Entrez dans les 4 colonnes à droite les informations du 7e exploitant",
        # Col 47: AV
        'Modalité d\'exploitation de l\'ADS\n"Salarié", "Locataire gérant", "Locataire coopérateur", "Titulaire exploitant" ou "Autre"',
        # Col 48: AW
        "Nom de l'exploitant de l'ADS",
        # Col 49: AX
        "SIRET de l'exploitant de l'ADS",
        # Col 50: AY
        "Numéro de la carte professionnelle",
        # Col 51: AZ
        "Entrez dans les 4 colonnes à droite les informations du 8e exploitant",
        # Col 52: BA
        'Modalité d\'exploitation de l\'ADS\n"Salarié", "Locataire gérant", "Locataire coopérateur", "Titulaire exploitant" ou "Autre"',
        # Col 53: BB
        "Nom de l'exploitant de l'ADS",
        # Col 54: BC
        "SIRET de l'exploitant de l'ADS",
        # Col 55: BD
        "Numéro de la carte professionnelle",
        # Col 56: BE
        "Entrez dans les 4 colonnes à droite les informations du 9e exploitant",
        # Col 57: BF
        'Modalité d\'exploitation de l\'ADS\n"Salarié", "Locataire gérant", "Locataire coopérateur", "Titulaire exploitant" ou "Autre"',
        # Col 58: BG
        "Nom de l'exploitant de l'ADS",
        # Col 59: BH
        "SIRET de l'exploitant de l'ADS",
        # Col 60: BI
        "Numéro de la carte professionnelle",
    )

    def __init__(self):
        self.excel = Excel(self.COLUMNS)

    def check_header(self, cols):
        """Make sure the header has the columns we expect."""
        for idx, (col, exp) in enumerate(itertools.zip_longest(cols, self.COLUMNS)):
            if col == exp or col.strip() == exp.strip():
                continue
            raise ValueError(
                f"\n=> Colonne {self.excel.idx_to_colname(idx)}: valeur inattendue:\n{col}\n\n=> Valeur attendue:\n{exp}"
            )

    def fmt_col_error(self, msg, value, idx):
        return ValueError(f"{msg} (colonne {self.excel.idx_to_colname(idx)}): {value}")

    def load_ads(self, cols):
        departement = self.find_departement(
            cols[self.excel.idx("numéro du département")]
        )
        commune = self.find_commune(
            departement,
            cols[self.excel.idx("nom de la commune")],
        )
        ads_manager = self.find_ads_manager(commune)
        ads_number = cols[
            self.excel.idx(
                "numéro de l'ads",
                exact=True,
            )
        ]
        ads = self.find_existing_ads(ads_manager, ads_number)
        if ads:
            exists = True
        else:
            ads = ADS(ads_manager=ads_manager, number=ads_number)
            exists = False

        ads.ads_creation_date = self.parse_date(
            cols,
            self.excel.idx("date de création"),
        )
        ads.ads_renew_date = self.parse_date(
            cols,
            self.excel.idx("date du dernier renouvellement"),
        )
        ads.attribution_date = self.parse_date(
            cols,
            self.excel.idx("date d'attribution"),
        )
        ads.accepted_cpam = self.parse_bool(
            cols,
            self.excel.idx("véhicule conventionné CPAM"),
        )
        ads.immatriculation_plate = self.parse_license_plate(
            cols,
            self.excel.idx(
                "plaque d'immatriculation",
                exact=True,
            ),
        )
        ads.vehicle_compatible_pmr = self.parse_bool(
            cols,
            self.excel.idx("compatible PMR"),
        )
        ads.owner_name = self.parse_owner_name(
            cols,
            self.excel.idx(
                "titulaire de l'ads",
                exact=True,
            ),
        )
        ads.owner_siret = self.parse_siret(cols, self.excel.idx("siret du titulaire"))
        ads.owner_phone = self.parse_phone(
            cols, self.excel.idx("téléphone fixe du titulaire"), mobile=False
        )
        ads.owner_mobile = self.parse_phone(
            cols, self.excel.idx("téléphone mobile du titulaire"), mobile=True
        )
        ads.owner_email = self.parse_email(
            cols,
            self.excel.idx("email du titulaire"),
        )

        ads.used_by_owner = self.parse_bool(
            cols,
            self.excel.idx("ads exploitée par son titulaire"),
        )

        # ADS without a creation date shoudl not have the field used_by_owner set
        if not ads.ads_creation_date:
            ads.used_by_owner = None
        # New ADS have to be used by the owner. If the ADS is new and the excel
        # contains true for the column "used by owner", we set the database
        # field to None to avoid integrity errors.
        elif (
            ads.ads_creation_date >= datetime.date(2014, 10, 1)
            and ads.used_by_owner is True
        ):
            ads.used_by_owner = None

        ads.owner_license_number = self.parse_license_number(
            cols, self.excel.idx("carte professionnelle du titulaire")
        )

        if not ads.attribution_type:
            ads.attribution_type = ""
        if not ads.attribution_reason:
            ads.attribution_reason = ""

        self.load_ads_users(cols, ads)
        return ads, exists

    def load_ads_users(self, cols, ads):
        """Load the ADS users from the excel file"""
        for i in range(9):
            idx = self.excel.nidx("nom de l'exploitant", i)
            if cols[idx]:
                raise self.fmt_col_error(
                    "Ce script ne permet pas encore d'importer les exploitants de l'ADS. Toutes les colonnes doivent rester vides",
                    cols[idx],
                    idx,
                )

            idx = self.excel.nidx("siret de l'exploitant", i)
            if cols[idx]:
                raise self.fmt_col_error(
                    "Ce script ne permet pas encore d'importer les exploitants de l'ADS. Toutes les colonnes doivent rester vides",
                    cols[idx],
                    cols[idx],
                    idx,
                )

            idx = self.excel.nidx("numéro de la carte professionnelle", i, exact=True)
            if cols[idx]:
                raise self.fmt_col_error(
                    "Ce script ne permet pas encore d'importer les exploitants de l'ADS. Toutes les colonnes doivent rester vides",
                    cols[idx],
                    idx,
                )

    @functools.cache
    def find_departement(self, numero):
        query = Prefecture.objects.filter(numero=numero)
        res = query.all()
        if len(res) == 0:
            raise ValueError(f"Département {numero} inconnu")
        if len(res) > 1:
            raise ValueError(f"Département {numero} ambigu ({len(res)} résultats)")
        return res[0]

    def normalize(self, value):
        """Remove all the special chars of `value`. Useful to compare two names."""
        return "".join(
            c
            for c in unidecode(value)
            if c in string.ascii_letters or c in string.digits
        ).lower()

    @functools.cache
    def find_commune(self, departement, name):
        query = Commune.objects.filter(
            departement=departement.numero, libelle__iexact=name
        )
        res = query.all()
        if len(res) == 1:
            return res[0]

        query = Commune.objects.filter(departement=departement.numero)
        normalized_name = self.normalize(name)
        candidates = []
        for commune in query.all():
            if self.normalize(commune.libelle) == normalized_name:
                candidates.append(commune)

        if len(candidates) == 0:
            raise ValueError(
                f"Commune {name} inconnue dans le département {departement}"
            )
        elif len(candidates) > 1:
            raise ValueError(
                f"Commune {name} ambiguë dans le département {departement}. Résultats trouvés: {', '.join((candidate.libelle for candidate in candidates))}"
            )
        return candidates[0]

    @functools.cache
    def find_ads_manager(self, commune):
        return ADSManager.objects.filter(
            content_type=ContentType.objects.get_for_model(Commune),
            object_id=commune.id,
        ).get()

    def find_existing_ads(self, ads_manager, numero):
        return ADS.objects.filter(ads_manager=ads_manager, number=numero).first()

    def parse_date(self, cols, idx):
        """Convert datetime to a value"""
        value = cols[idx]
        if not value:
            return None
        if not isinstance(value, datetime.datetime):
            raise self.fmt_col_error("Date invalide", value, idx)
        return value.date()

    def parse_bool(self, cols, idx):
        """Convert a string to a boolean value"""
        value = cols[idx]
        if not value:
            return None
        if value.lower().strip() == "oui":
            return True
        elif value.lower().strip() == "non":
            return False
        raise self.fmt_col_error("Valeur invalide", value, idx)

    def parse_license_plate(self, cols, idx):
        return cols[idx] or ""

    def parse_owner_name(self, cols, idx):
        return cols[idx] or ""

    def parse_siret(self, cols, idx):
        siret = str(cols[idx])
        if siret:
            try:
                validate_siret(siret)
            except Exception as exc:
                raise self.fmt_col_error("Siret invalide", siret, idx)
        return siret

    def parse_phone(self, cols, idx, mobile=False):
        if not cols[idx]:
            return ""
        phone = "".join(str(cols[idx]).split())
        if len(phone) != 10:
            raise self.fmt_col_error(
                "Numéro de téléphone invalide, doit faire 10 chiffres", cols[idx], idx
            )
        if not phone.startswith("0"):
            raise self.fmt_col_error(
                "Numéro de téléphone invalide, doit commencer par 0", cols[idx], idx
            )
        if mobile and phone:
            if not phone.startswith("06") and not phone.startswith("07"):
                raise self.fmt_col_error(
                    "Numéro de téléphone invalide, doit commencer par 06 ou 07",
                    cols[idx],
                    idx,
                )
        elif not mobile and phone:
            if phone.startswith("06") or phone.startswith("07"):
                raise self.fmt_col_error(
                    "Numéro de téléphone invalide, ne doit pas commencer par 06 ou 07",
                    cols[idx],
                    idx,
                )
        return phone

    def parse_email(self, cols, idx):
        if not cols[idx]:
            return ""
        if not re.match(r"^.*@.*\..*$", cols[idx]):
            raise self.fmt_col_error("Email invalide", cols[idx], idx)
        return cols[idx]

    def parse_license_number(self, cols, idx):
        return cols[idx] or ""


class Command(BaseCommand):
    help = "Import ADS from CSV file"

    def add_arguments(self, parser):
        parser.add_argument("-f", "--ads-file", required=True)

    def _log(self, level, msg, icon=None):
        if not icon:
            icon = (level == self.style.SUCCESS) and "✅" or "❌"
        sys.stdout.write(level(f"{icon} {msg}\n"))

    def handle(self, ads_file, **opts):
        workbook = openpyxl.load_workbook(ads_file)
        sheet = workbook.active
        importer = ADSImporter()

        header = next(sheet.iter_rows(values_only=True))
        importer.check_header(header)

        has_error = False
        ads_list = []

        self._log(self.style.SUCCESS, "Préparation de l'import...")

        for idx, cols in enumerate(sheet.iter_rows(min_row=2, values_only=True)):
            try:
                ads, exists = importer.load_ads(cols)
                if exists:
                    self._log(
                        self.style.SUCCESS,
                        f"Ligne {idx+2}: ADS {ads.id} prête à être mise à jour",
                    )
                else:
                    self._log(
                        self.style.SUCCESS,
                        f"Ligne {idx+2}: préparation d'une nouvelle ADS",
                    )
                ads_list.append(ads)
            except ValueError as exc:
                self._log(self.style.ERROR, f"Line {idx+2}: {exc}")
                has_error = True

        if has_error:
            self._log(
                self.style.ERROR,
                "Échec de la préparation de l'import. Réglez les erreurs et réessayez.",
            )
            return

        self._log(
            self.style.SUCCESS,
            "Préparation de l'import terminée. Enregistrement des ADS...",
        )

        # Save all ADS in a single transaction, so that if one fails, all are rolled back
        try:
            last_exc = None
            with transaction.atomic():
                for idx, ads in enumerate(ads_list):
                    try:
                        # For each ADS, we create a new transaction. If one
                        # fails, we still try to save the others but the outer
                        # transaction will be rolled back.
                        with transaction.atomic():
                            ads.save()
                            self._log(
                                self.style.SUCCESS,
                                f"Ligne {idx+1}: ADS numéro {ads.number} enregistrée",
                            )
                    except Exception as exc:
                        last_exc = exc
                        self._log(
                            self.style.ERROR,
                            f"Ligne {idx+1}: échec de l'import de l'ADS {ads.number}: {exc}",
                        )

                if last_exc:
                    raise last_exc
        except:
            self._log(
                self.style.ERROR, "Échec de l'import, aucune ADS n'a été enregistrée"
            )
        else:
            self._log(self.style.SUCCESS, "Enregistrement terminé.")
