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
