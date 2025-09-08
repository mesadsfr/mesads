from django.contrib.contenttypes.fields import GenericRelation
from django.db import models


class AdministrationModel(models.Model):
    """Implemented by Commune, Prefecture and EPCI."""

    class Meta:
        abstract = True

    def type_name(self):
        """Human readable name of the administration type (commune, prefecture, epci)."""
        raise NotImplementedError

    def text(self):
        """Name of the administration."""
        raise NotImplementedError

    def display_text(self):
        """Human readable name of this administration."""
        raise NotImplementedError

    def display_fulltext(self):
        """Like display_text(), buf prefixed with the correct french article "la" or "l'"."""
        raise NotImplementedError


class CommuneManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(type_commune="COM")


class Commune(AdministrationModel):
    """Communes of France. Inserted by the django admin command
    "load_communes".

    :param insee: INSEE code of the commune. Field "COM" of the CSV file
        provided by INSEE.

    :param departement: Departement code of the commune. Field "DEP" of the CSV
        file provided by INSEE.

    :param libelle: Human readable name for the commune. Field "LIBELLE" of the
        CSV file provided by insee.
    """

    objects = CommuneManager()
    all_objects = models.Manager()

    class Meta:
        # Necessary to set the constraint as deferrable, because during import
        # in update_communes.py, we need to defer checks to avoid constraint
        # violations.
        constraints = [
            models.UniqueConstraint(
                fields=["type_commune", "insee"],
                name="fradm_commune_type_commune_insee",
                deferrable=models.Deferrable.IMMEDIATE,
            ),
        ]

    def type_name(self):
        return "commune"

    def text(self):
        return self.libelle

    def display_text(self):
        if self.libelle.lower()[0:1] in "aeiouy":
            return f"commune d'{self.libelle}"
        return f"commune de {self.libelle}"

    def display_fulltext(self):
        return f"la {self.display_text()}"

    def __str__(self):
        return f"{self.departement} - {self.libelle} (INSEE: {self.insee})"

    TYPE_COMMUNE = (
        ("COM", "Commune"),
        ("COMA", "Commune associée"),
        ("COMD", "Commune déléguée"),
        ("ARM", "Arrondissement municipal"),
    )

    type_commune = models.CharField(
        max_length=16,
        choices=TYPE_COMMUNE,
        blank=False,
        null=False,
        verbose_name="Type de commune",
    )

    insee = models.CharField(max_length=16, null=False, blank=False)
    departement = models.CharField(max_length=16, blank=False, null=False)
    libelle = models.CharField(max_length=255, null=False, blank=False)

    ads_managers = GenericRelation("app.ADSManager", related_query_name="commune")


class Prefecture(AdministrationModel):
    """Departement of France, Inserted by the django admin command
    "load_prefectures".

    :param numero: numero of the departement. Field "DEP" of the CSV file
        provided by INSEE.

    :param libelle: Human readable name for the commune. Field "LIBELLE" of the
        CSV file provided by insee.
    """

    numero = models.CharField(max_length=16, null=False, blank=False, unique=True)
    libelle = models.CharField(max_length=255, null=False, blank=False, unique=True)

    ads_managers = GenericRelation("app.ADSManager", related_query_name="prefecture")

    def type_name(self):
        return "préfecture"

    def text(self):
        return self.libelle

    def display_text(self):
        # Special case when "libelle" equals "Préfecture de Police de Paris":
        # return "préfecture de xxx" (with lowercase "p" at the beginning)
        if self.libelle.lower().startswith("préfecture"):
            return "p" + self.libelle[1:]
        elif self.libelle.lower()[0:1] in "aeiouy":
            return f"préfecture d'{self.libelle}"
        return f"préfecture de {self.libelle}"

    def display_fulltext(self):
        return f"la {self.display_text()}"

    def __str__(self):
        return f"{self.numero} - {self.libelle}"


class EPCI(AdministrationModel):
    """EPCI stands for Établissement Public de Coopération Intercommunale.
    Inserted by the django admin command "load_epci".

    :param siren: SIREN of the EPCI, field "siren_epci" of the CSV file
        provided by INSEE.

    :param departement: Departement of the EPCI, field "dep_epci" of the CSV file
        provided by INSEE.

    :param name: Name of the EPCI, field "nom_complet" of the CSV file provided
        by INSEE.
    """

    class Meta:
        verbose_name = "EPCI"
        verbose_name_plural = "EPCI"
        unique_together = (("departement", "name"),)

    def type_name(self):
        return "EPCI"

    def text(self):
        return self.name

    def display_text(self):
        return f"EPCI {self.name}"

    def display_fulltext(self):
        return f"l'{self.display_text()}"

    def __str__(self):
        return self.name

    siren = models.CharField(max_length=64, blank=False, null=False, unique=True)
    departement = models.CharField(max_length=16, blank=False, null=False)
    name = models.CharField(max_length=255, blank=False, null=False)

    ads_managers = GenericRelation("app.ADSManager", related_query_name="epci")
