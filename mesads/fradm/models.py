from django.db import models


class Commune(models.Model):
    """Communes of France. Inserted by the django admin command
    "load-communes".
    """
    insee = models.CharField(max_length=16, null=False, blank=False, primary_key=True)
    libelle = models.CharField(max_length=255, null=False, blank=False)
