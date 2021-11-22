from django.db import models


class Commune(models.Model):
    """Communes of France. Inserted by the django admin command
    "load_communes".

    :param insee: INSEE code of the commune. Field "COM" of the CSV file
        provided by INSEE.

    :param libelle: Human readable name for the commune. Field "LIBELLE" of the
        CSV file provided by insee.
    """
    insee = models.CharField(max_length=16, null=False, blank=False, primary_key=True)
    libelle = models.CharField(max_length=255, null=False, blank=False)


class Prefecture(models.Model):
    """Departement of France, Inserted by the django admin command
    "load_prefectures".

    :param numero: numero of the departement. Field "DEP" of the CSV file
        provided by INSEE.

    :param libelle: Human readable name for the commune. Field "LIBELLE" of the
        CSV file provided by insee.
    """
    numero = models.CharField(max_length=16, null=False, blank=False, primary_key=True)
    libelle = models.CharField(max_length=255, null=False, blank=False)


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
        verbose_name_plural = 'EPCIs'

    siren = models.CharField(max_length=64, blank=False, null=False, primary_key=True)
    departement = models.CharField(max_length=16, blank=False, null=False)
    name = models.CharField(max_length=255, blank=False, null=False)
