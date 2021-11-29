from django.contrib.contenttypes.fields import GenericRelation
from django.db import models


class Commune(models.Model):
    """Communes of France. Inserted by the django admin command
    "load_communes".

    :param insee: INSEE code of the commune. Field "COM" of the CSV file
        provided by INSEE.

    :param departement: Departement code of the commune. Field "DEP" of the CSV
        file provided by INSEE.

    :param libelle: Human readable name for the commune. Field "LIBELLE" of the
        CSV file provided by insee.
    """
    class Meta:
        unique_together = (
            ('departement', 'libelle'),
        )

    def __str__(self):
        return f'{self.departement} - {self.libelle} (INSEE: {self.insee})'

    insee = models.CharField(max_length=16, null=False, blank=False, unique=True)
    departement = models.CharField(max_length=16, blank=False, null=False)
    libelle = models.CharField(max_length=255, null=False, blank=False)

    ads_managers = GenericRelation(
        'app.ADSManager',
        related_query_name='commune'
    )


class Prefecture(models.Model):
    """Departement of France, Inserted by the django admin command
    "load_prefectures".

    :param numero: numero of the departement. Field "DEP" of the CSV file
        provided by INSEE.

    :param libelle: Human readable name for the commune. Field "LIBELLE" of the
        CSV file provided by insee.
    """
    numero = models.CharField(max_length=16, null=False, blank=False, unique=True)
    libelle = models.CharField(max_length=255, null=False, blank=False, unique=True)

    ads_managers = GenericRelation(
        'app.ADSManager',
        related_query_name='prefecture'
    )

    def __str__(self):
        return f'{self.numero} - {self.libelle}'


class EPCI(models.Model):
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
        verbose_name = 'EPCI'
        verbose_name_plural = 'EPCI'
        unique_together = (
            ('departement', 'name'),
        )

    def __str__(self):
        return self.name

    siren = models.CharField(max_length=64, blank=False, null=False, unique=True)
    departement = models.CharField(max_length=16, blank=False, null=False)
    name = models.CharField(max_length=255, blank=False, null=False)

    ads_managers = GenericRelation(
        'app.ADSManager',
        related_query_name='epci'
    )
