from django.db import models
from django.db.models import Max, F

import reversion

from mesads.fradm.models import Prefecture


@reversion.register
class Proprietaire(models.Model):
    def __str__(self):
        return self.nom

    created_at = models.DateTimeField(auto_now_add=True, null=False)
    last_update_at = models.DateTimeField(auto_now=True, null=True)

    nom = models.CharField(
        null=False,
        blank=False,
        max_length=256,
        help_text="Nom du propriétaire",
    )

    siret = models.CharField(
        null=False,
        blank=True,
        max_length=64,
        help_text="SIRET du propriétaire",
    )

    telephone = models.CharField(
        null=False,
        blank=True,
        max_length=32,
    )

    email = models.EmailField(
        null=False,
        blank=True,
        max_length=256,
    )


class VehiculeManager(models.Manager):
    def get_next_number(self, departement):
        """Get the current last number for the specified departement."""
        try:
            last_vehicule = self.filter(departement=departement).latest("id")
        except Vehicule.DoesNotExist:
            return f"{departement.numero:02s}-01"

        last_numero = int(last_vehicule.numero.split("-")[1])
        return f"{departement.numero:02s}-{last_numero+1:02d}"


@reversion.register
class Vehicule(models.Model):
    objects = VehiculeManager()

    def __str__(self):
        return f"Véhicule {self.numero} du département {self.departement.numero} - {self.proprietaire}"

    def save(self, *args, **kwargs):
        # Automatically set the number when creating a new instance.
        if not self.pk:
            self.numero = Vehicule.objects.get_next_number(self.departement)
        return super().save(*args, **kwargs)

    created_at = models.DateTimeField(auto_now_add=True, null=False)
    last_update_at = models.DateTimeField(auto_now=True, null=True)

    proprietaire = models.ForeignKey(
        Proprietaire,
        on_delete=models.RESTRICT,
        null=False,
        help_text="Propriétaire du véhicule",
    )

    departement = models.ForeignKey(Prefecture, on_delete=models.RESTRICT, null=False)

    numero = models.CharField(
        null=False,
        blank=True,
        max_length=16,
        help_text="Numéro unique identifiant le véhicule relais",
        unique=True,
    )

    immatriculation = models.CharField(
        null=False,
        blank=True,
        max_length=32,
        help_text="Plaque d'immatriculation du véhicule",
    )

    modele = models.CharField(
        null=False,
        blank=True,
        max_length=256,
        help_text="Marque, modèle et série du véhicule",
    )

    MOTIRISATIONS = (
        ("essence", "Essence"),
        ("diesel", "Diesel"),
        ("hybride", "Hybride"),
        ("hybride_rechargeable", "Hybride rechargeable"),
        ("electrique", "Electrique"),
        ("GPL", "GPL"),
        ("E85", "E85"),
    )

    motorisation = models.CharField(
        max_length=64,
        choices=MOTIRISATIONS,
        blank=True,
        null=False,
        help_text="Motorisation du véhicule",
    )

    date_mise_circulation = models.DateField(
        null=True,
        blank=True,
        help_text="Date de mise en circulation du véhicule",
    )

    nombre_places = models.IntegerField(
        null=True,
        blank=True,
        help_text="Nombre de places assises (mention S1 sur la carte grise)",
    )

    pmr = models.BooleanField(
        null=True,
        blank=True,
        help_text="Le véhicule est-il accessible aux personnes à mobilité réduite ?",
    )
