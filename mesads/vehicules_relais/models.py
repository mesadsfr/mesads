import unicodedata

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

import reversion

from markdownx.models import MarkdownxField

from mesads.fradm.models import Commune, Prefecture
from mesads.app.models import (
    SmartValidationMixin,
    validate_siret,
    CharFieldsStripperMixin,
    SoftDeleteMixin,
    SoftDeleteManager,
)


@reversion.register
class Proprietaire(
    SmartValidationMixin, CharFieldsStripperMixin, SoftDeleteMixin, models.Model
):
    class Meta:
        verbose_name = "Propriétaire de véhicules relais"
        verbose_name_plural = "Propriétaires de véhicules relais"

    def __str__(self):
        return self.nom

    SMART_VALIDATION_WATCHED_FIELDS = {
        "siret": lambda _, siret: validate_siret(siret),
    }

    created_at = models.DateTimeField(auto_now_add=True, null=False)
    last_update_at = models.DateTimeField(auto_now=True, null=True)

    nom = models.CharField(
        null=False,
        blank=False,
        max_length=256,
        verbose_name="Nom du propriétaire",
    )

    siret = models.CharField(
        null=False,
        blank=True,
        max_length=64,
        verbose_name="SIRET du propriétaire",
    )

    telephone = models.CharField(
        null=False, blank=True, max_length=32, verbose_name="Numéro de téléphone"
    )

    email = models.EmailField(
        null=False, blank=True, max_length=256, verbose_name="Adresse email"
    )

    users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True)


class VehiculeManager(SoftDeleteManager):
    def get_next_number(self, departement):
        """Get the current last number for the specified departement."""
        try:
            last_vehicule = Vehicule.with_deleted.filter(
                departement=departement
            ).latest("id")
        except Vehicule.DoesNotExist:
            return f"{departement.numero:02s}-01"

        last_numero = int(last_vehicule.numero.split("-")[1])
        return f"{departement.numero:02s}-{last_numero+1:02d}"


def clean_immatriculation(s):
    """Replace all Unicode dash-punctuation with ASCII hyphen."""
    s = unicodedata.normalize("NFKC", s)
    return "".join("-" if unicodedata.category(ch) == "Pd" else ch for ch in s)


@reversion.register
class Vehicule(CharFieldsStripperMixin, SoftDeleteMixin, models.Model):
    class Meta:
        verbose_name = "Véhicule relais"
        verbose_name_plural = "Véhicules relais"

    objects = VehiculeManager()

    def __str__(self):
        return f"Véhicule {self.numero} du département {self.departement.numero} - {self.proprietaire}"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__initial_departement = getattr(self, "departement", None)
        self.__initial_immatriculation = self.immatriculation

    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)

        if (
            self.__initial_immatriculation
            and self.__initial_immatriculation != self.immatriculation
        ):
            raise ValidationError(
                {
                    "immatriculation": "Une fois le véhicule créé, la plaque d'immatriculation ne peut pas être modifiée. "
                    "Si vous souhaitez réellement changer la plaque, veuillez supprimer "
                    "le véhicule et en enregistrer un nouveau, ce qui entrainera la création d'un nouveau numéro de véhicule."
                }
            )

        if (
            self.__initial_departement
            and self.__initial_departement != self.departement
        ):
            raise ValidationError(
                {
                    "departement": "Une fois le véhicule créé, le département ne peut pas être modifié. "
                    "Si vous souhaitez réellement changer le département, veuillez supprimer "
                    "le véhicule et en enregistrer un nouveau."
                }
            )

    def save(self, *args, **kwargs):
        # Automatically set the number when creating a new instance.
        if not self.pk:
            self.numero = Vehicule.objects.get_next_number(self.departement)

        self.immatriculation = clean_immatriculation(self.immatriculation)

        return super().save(*args, **kwargs)

    def main_features(self):
        ret = []
        if self.motorisation == "electrique":
            ret.append("Véhicule électrique")
        elif self.motorisation == "hybride":
            ret.append("Véhicule hybride")
        elif self.motorisation == "hybride_rechargeable":
            ret.append("Véhicule hybride rechargeable")

        if self.pmr:
            ret.append("Accès PMR")
        return ret

    created_at = models.DateTimeField(auto_now_add=True, null=False)
    last_update_at = models.DateTimeField(auto_now=True, null=True)

    proprietaire = models.ForeignKey(
        Proprietaire,
        on_delete=models.RESTRICT,
        null=False,
        help_text="Propriétaire du véhicule",
    )

    departement = models.ForeignKey(
        Prefecture,
        on_delete=models.RESTRICT,
        null=False,
        verbose_name="Département du véhicule relais",
    )

    numero = models.CharField(
        null=False,
        blank=True,
        max_length=16,
        verbose_name="Numéro unique identifiant le véhicule relais",
        unique=True,
    )

    immatriculation = models.CharField(
        null=False,
        blank=True,
        max_length=32,
        verbose_name="Plaque d'immatriculation du véhicule",
        help_text="La plaque d'immatriculation du véhicule ne peut pas être modifiée une fois le véhicule enregistré.",
    )

    modele = models.CharField(
        null=False,
        blank=True,
        max_length=256,
        verbose_name="Marque, modèle et série du véhicule",
    )

    MOTIRISATIONS = (
        ("essence", "Essence"),
        ("diesel", "Diesel"),
        ("hybride", "Hybride"),
        ("hybride_rechargeable", "Hybride rechargeable"),
        ("electrique", "Electrique"),
        ("GPL", "GPL"),
        ("E85", "E85"),
        ("h2", "Hydrogène"),
    )

    motorisation = models.CharField(
        max_length=64,
        choices=MOTIRISATIONS,
        blank=True,
        null=False,
        verbose_name="Motorisation du véhicule",
    )

    date_mise_circulation = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date de mise en circulation du véhicule",
    )

    nombre_places = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Nombre de places assises",
        help_text="Mention S1 sur la carte grise",
    )

    pmr = models.BooleanField(
        null=True,
        blank=True,
        verbose_name="Le véhicule est accessible aux personnes à mobilité réduite ?",
        help_text=(
            "Vous pouvez retrouver cette information sur la mention « J.3 : handicap » de la "
            "carte grise du véhicule concerné par l'ADS."
        ),
    )

    commune_localisation = models.ForeignKey(
        Commune,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        verbose_name="Commune où est situé le véhicule",
    )


@reversion.register
class DispositionSpecifique(CharFieldsStripperMixin, models.Model):
    """DispositionSpecifique stores a message that can be displayed on the
    Vehicule form registered to a specific departement."""

    class Meta:
        verbose_name = "Disposition spécifique"
        verbose_name_plural = "Dispositions spécifiques"

    departement = models.OneToOneField(
        Prefecture,
        on_delete=models.RESTRICT,
        null=False,
        verbose_name="Département concerné",
    )

    message = MarkdownxField(
        null=False,
        blank=True,
        verbose_name="Message à afficher sur le formulaire de création de véhicule",
        help_text="Format Markdown autorisé",
    )
