from datetime import date, datetime
import logging
import os
import re

import requests

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone
from django.utils.html import mark_safe

import reversion

from django_cleanup import cleanup

from mesads.fradm.models import Commune, EPCI, Prefecture


class SoftDeleteManager(models.Manager):
    """Manager to add a soft delete feature to a model.

    This manager overrides the `get_queryset` method to filter out objects that
    have a `deleted_at` field set.
    """

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class SoftDeleteMixin(models.Model):
    """Mixin to add a soft delete feature to a model.

    This mixin adds a `deleted_at` field to the model, and overrides the
    `delete` method to set the field to True instead of actually deleting the
    object.
    """

    class Meta:
        abstract = True

    objects = SoftDeleteManager()
    with_deleted = models.Manager()

    deleted_at = models.DateTimeField(
        blank=True,
        null=True,
        default=None,
        verbose_name="Date de suppression",
        help_text="Date de suppression de l'objet. Si cette date est renseignée, l'objet est considéré comme supprimé.",
    )

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save()


class SmartValidationMixin:
    """Override clean() to only validate fields that have changed."""

    SMART_VALIDATION_WATCHED_FIELDS = None

    def __init__(self, *args, **kwargs):
        """Store the initial value for the watched fields."""
        assert self.SMART_VALIDATION_WATCHED_FIELDS
        super().__init__(*args, **kwargs)
        self.__smart_validation_initial_values = {
            name: getattr(self, name)
            for name in self.SMART_VALIDATION_WATCHED_FIELDS.keys()
        }

    def clean(self, *args, **kwargs):
        """If any of the watched fields changed, revalidate it."""
        super().clean(*args, **kwargs)
        for key, initial_value in self.__smart_validation_initial_values.items():
            if getattr(self, key) != initial_value:
                validator = self.SMART_VALIDATION_WATCHED_FIELDS[key]
                try:
                    validator(self, getattr(self, key))
                except Exception as exc:
                    raise ValidationError({key: exc})


class CharFieldsStripperMixin:
    """Strip all char fields."""

    def clean(self, *args, **kwargs):
        for field in self._meta.fields:
            if isinstance(field, models.CharField):
                value = getattr(self, field.name)
                # Usually our CharFields are not nullable, but make sure we
                # don't attempt to strip None.
                if value is not None:
                    stripped = self.strip(value)
                    setattr(self, field.name, stripped)
        return super().clean(*args, **kwargs)

    def strip(self, value):
        value = value.strip()
        if value == "-":
            value = ""
        return value


def validate_no_ads_declared(ads_manager, value):
    if ads_manager.ads_set.count() > 0 and value:
        raise ValidationError(
            "Impossible de déclarer que le gestionnaire ne gère aucune ADS, puisque des ADS sont déjà déclarées."
        )
    if ads_manager.no_ads_declared and ads_manager.epci_delegate:
        raise ValidationError(
            "Impossible de déclarer que le gestionnaire ne gère aucune ADS en même temps qu'un EPCI gestionnaire des ADS."
        )


class ADSManager(SmartValidationMixin, models.Model):
    """Authority who can register a new ADS. Either a Prefecture, a Commune or
    a EPCI.
    """

    class Meta:
        verbose_name = "Gestionnaire ADS"
        verbose_name_plural = "Gestionnaires ADS"
        unique_together = (("content_type", "object_id"),)

        # This is required, otherwise reverse relationship don't get the
        # attribute ads_count set by ADSManagerModelManager.
        base_manager_name = "objects"

    SMART_VALIDATION_WATCHED_FIELDS = {
        "no_ads_declared": validate_no_ads_declared,
        "epci_delegate": validate_no_ads_declared,
    }

    def __str__(self):
        return f"{self.content_type.name} - {self.content_object}"

    def human_name(self):
        if issubclass(self.content_type.model_class(), EPCI):
            return (
                f"EPCI — {self.content_object.name} ({self.content_object.departement})"
            )
        elif issubclass(self.content_type.model_class(), Prefecture):
            return f"Préfecture — {self.content_object.libelle} ({self.content_object.numero})"
        elif issubclass(self.content_type.model_class(), Commune):
            return (
                f"Commune — {self.content_object.libelle} ({self.content_object.insee})"
            )
        # Never reached
        return str(self)  # pragma: nocover

    administrator = models.ForeignKey(
        "ADSManagerAdministrator", on_delete=models.RESTRICT, null=False
    )

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to=models.Q(app_label="fradm", model="commune")
        | models.Q(
            app_label="fradm",
            model="epci",
        )
        | models.Q(
            app_label="fradm",
            model="prefecture",
        ),
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    no_ads_declared = models.BooleanField(
        null=False,
        default=False,
        verbose_name="L'administration ne gère aucune ADS",
        help_text="Cochez cette case si le gestionnaire ne gère aucune ADS.",
    )

    epci_delegate = models.ForeignKey(
        EPCI,
        on_delete=models.RESTRICT,
        blank=True,
        null=True,
        verbose_name="EPCI gestionnaire des ADS",
        help_text="Si la gestion des ADS de votre administration est déléguée à un EPCI, sélectionnez-le ici.",
    )

    is_locked = models.BooleanField(
        default=False,
        help_text="Cochez cette case pour empêcher la gestion manuelle des ADS pour cette administration",
    )


@cleanup.ignore
class ADSManagerDecree(models.Model):
    """Represents the decree that limits the number of ADS that can be created for administration."""

    def __str__(self):
        return f"Decree for ADSManager {self.ads_manager.id}"

    def get_filename(self, filename):
        now = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        filename = os.path.basename(filename)
        name = "/".join(
            [
                "ads_managers_decrees",
                "%s - %s"
                % (
                    self.ads_manager.id,
                    self.ads_manager.content_object.display_text(),
                ),
                f"{now} - {filename}",
            ]
        )
        return name

    def human_filename(self):
        """Reverse of get_legal_filename."""
        basename = os.path.basename(self.file.name)
        return " ".join(basename.split("-")[3:])[1:]

    def exists_in_storage(self):
        """Returns False if file has been removed from storage, either manually
        or after a database restore."""
        return self.file.storage.exists(self.file.name)

    creation_date = models.DateTimeField(
        auto_now_add=True, null=False, verbose_name="Date de création du fichier"
    )

    ads_manager = models.ForeignKey(
        ADSManager, on_delete=models.CASCADE, null=False, blank=False
    )

    file = models.FileField(upload_to=get_filename, null=False, blank=False)


@reversion.register
class ADSManagerRequest(models.Model):
    """User request to become ADSManager. Has to be accepted by the
    administrator (ie. the prefecture) of the ADSManager.
    """

    def __str__(self):
        return f"Requete de {self.user} pour être administrateur de {self.ads_manager}"

    class Meta:
        unique_together = (("user", "ads_manager"),)
        verbose_name = "Demande pour devenir gestionnaire ADS"
        verbose_name_plural = "Demandes pour devenir gestionnaire ADS"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=False, blank=False
    )
    ads_manager = models.ForeignKey(
        ADSManager,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
    )
    created_at = models.DateTimeField(auto_now_add=True, null=False)
    last_update_at = models.DateTimeField(auto_now=True, null=True)
    accepted = models.BooleanField(null=True, default=None)


class ADSManagerAdministrator(models.Model):
    """Administrator with the ability to manage users of ADSManager.

    :param users: Users who can manage the list of ads_managers.

    :param ads_managers: ADSManager managed by this administrator.

    :param expected_ads_count: Number of ADSManager expected for this prefecture.
    """

    class Meta:
        verbose_name = "Administrateur des gestionnaires ADS"
        verbose_name_plural = "Administrateurs des gestionnaires ADS"

    def __str__(self):
        return f"Administrateur des gestionnaires de la préfecture {self.prefecture}"

    referent_emails = models.TextField(
        null=False,
        blank=True,
        help_text="Emails des référents de votre préfecture, à contacter pour les questions relative aux ADS.",
    )

    prefecture = models.OneToOneField(
        Prefecture, on_delete=models.CASCADE, null=False, blank=False
    )
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True)
    expected_ads_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Nombre de gestionnaires ADS attendus pour cette préfecture.",
    )

    def ordered_adsmanager_set(self):
        """Function helper to get the adsmanager set order by the administration
        name."""
        return (
            self.adsmanager_set.prefetch_related("content_object", "ads_set")
            .filter(Q(commune__type_commune="COM") | Q(commune__isnull=True))
            .order_by("commune__libelle", "epci__name", "prefecture__libelle")
        )


def validate_siret(value):
    if not value:
        return

    if not re.match(r"^\d{14}$", value):
        raise ValidationError("Un SIRET doit être composé de 14 numéros")

    if not settings.INSEE_TOKEN:
        return

    try:
        resp = requests.get(
            f"https://api.insee.fr/api-sirene/3.11/siret/{value}",
            headers={"X-INSEE-Api-Key-Integration": settings.INSEE_TOKEN},
            timeout=1,
        )

    # INSEE API did not answer fast enough, consider the number is valid
    except requests.exceptions.Timeout:
        logging.exception("Timeout while verifying SIRET validity. Skip validation.")
        return
    except requests.exceptions.RequestException:
        logging.exception(
            "Unknown error while verifying SIRET validity. Skip validation."
        )
        return

    # Ok
    if resp.status_code >= 200 and resp.status_code < 300:
        return

    if resp.status_code == 404:
        raise ValidationError(
            "D'après les données de l'INSEE, ce SIRET est invalide. Si le n° SIRET est récent, il est possible que les données de l'INSEE ne soient pas encore à jour. Dans ce cas, laissez ce champ vide puis complétez le d'ici quelques jours."
        )

    if resp.status_code == 429:
        logging.info(
            f"INSEE API rate limit reached, could not verify SIRET validity {value}"
        )
        return

    # SIRET is valid, but not diffusable
    #
    # "La loi permet aux personnes physiques de s'opposer à la diffusion de
    # leurs données: les siren et siret correspondants sont alors qualifiés de
    # «non-diffusibles»."
    try:
        resp_json = resp.json()
    except requests.exceptions.JSONDecodeError:
        pass
    else:
        if resp.status_code == 403 and "non diffusable" in resp_json.get(
            "header", {}
        ).get("message", ""):
            return

    # Unknown case, log it to sentry for future investigation
    logging.error(
        "Unknown return value from INSEE API while checking for SIRET validity",
        extra={
            "insee": value,
            "resp_status_code": resp.status_code,
            "resp": resp.text,
        },
    )


@reversion.register
class ADS(SmartValidationMixin, CharFieldsStripperMixin, models.Model):
    """Autorisation De Stationnement created by ADSManager."""

    class Meta:
        verbose_name = "ADS"
        verbose_name_plural = "ADS"

        constraints = [
            # To understand why we do not define violation_error_message here,
            # see the documentation of the method `unique_error_message`
            models.UniqueConstraint(
                fields=["number", "ads_manager_id"],
                name="unique_ads_number",
            ),
            models.CheckConstraint(
                check=Q(ads_creation_date__isnull=True)
                | Q(attribution_date__isnull=True)
                | Q(ads_creation_date__lte=F("attribution_date")),
                name="ads_creation_date_before_attribution_date",
                violation_error_message="La date de création de l'ADS doit être antérieure à la date d'attribution.",
            ),
            #
            # !!! Note !!! In SQL, comparing a date with NULL is always NULL so we need
            #
            # to check for NULL before comparing with a date.
            # That's why the constraints below always check date__isnull before date__gte or date__lt.
            #
            # Check attribution date:
            # - For new ADS, attribution date should be null
            # - For old ADS, attribution date can be set or not
            # - For unknown creation date, we allow attribution date to be set or not to avoid blocking the creation when we don't know the creation date
            models.CheckConstraint(
                check=(
                    Q(
                        ads_creation_date__isnull=False,
                        ads_creation_date__gte=date(2014, 10, 1),
                        attribution_date__isnull=True,
                    )
                    | Q(
                        ads_creation_date__isnull=False,
                        ads_creation_date__lt=date(2014, 10, 1),
                    )
                    | Q(ads_creation_date__isnull=True)
                ),
                name="attribution_date_null_for_new_ads",
                violation_error_message="La date d'attribution ne peut être renseignée que pour les ADS créées avant le 1er octobre 2014.",
            ),
            # Check renewal date nullable:
            # - For new ADS, renew date can be set or not
            # - For old ADS, renew date must always be empty
            # - For unknown creation date, we allow attribution date to be set or not to avoid blocking the creation when we don't know the creation date
            models.CheckConstraint(
                check=(
                    Q(
                        ads_creation_date__isnull=False,
                        ads_creation_date__gte=date(2014, 10, 1),
                    )
                    | Q(
                        ads_creation_date__isnull=False,
                        ads_creation_date__lt=date(2014, 10, 1),
                        ads_renew_date__isnull=True,
                    )
                    | Q(ads_creation_date__isnull=True, ads_renew_date__isnull=True)
                ),
                name="renew_date_null_for_old_ads",
                violation_error_message="La date de renouvellement ne peut être renseignée que pour les ADS créées après le 1er octobre 2014.",
            ),
            # Check renewal date content: if set, renewal date must be after the creation date
            models.CheckConstraint(
                check=Q(ads_renew_date__isnull=True)
                | Q(ads_renew_date__gte=F("ads_creation_date")),
                name="renew_date_after_creation_date",
                violation_error_message="La date de renouvellement de l'ADS doit être postérieure à la date de création.",
            ),
        ]

    SMART_VALIDATION_WATCHED_FIELDS = {
        "owner_siret": lambda _, siret: validate_siret(siret),
    }

    def __str__(self):
        return f"ADS {self.id}"

    def run_checks(self):
        """Raise an exception if the ADS is not valid"""
        if self.ads_manager.is_locked:
            raise ValidationError(
                "Il n'est pas possible d'apporter des modifications sur les ADS d'une administration verrouillée."
            )
        if self.ads_creation_date and self.ads_creation_date >= date(2014, 10, 1):
            existing_users = ADSUser.objects.filter(ads_id=self.id)
            if existing_users.count() > 1:
                raise ValidationError(
                    "Un seul exploitant peut être déclaré pour une ADS créée après le 1er octobre 2014."
                )
            if (
                existing_users.exists()
                and existing_users.first().status != "titulaire_exploitant"
            ):
                raise ValidationError(
                    "Le conducteur doit nécessairement être le titulaire de l'ADS (personne physique) pour une ADS créée après le 1er octobre 2014."
                )

    def save(self, check=True, *args, **kwargs):
        if check:
            self.run_checks()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.ads_manager.is_locked:
            raise ValidationError(
                "Il n'est pas possible de supprimer une ADS d'une administration verrouillée."
            )
        return super().delete(*args, **kwargs)

    UNIQUE_ERROR_MSG = "Une ADS avec ce numéro existe déjà. Supprimez l'ADS existante, ou utilisez un autre numéro."

    def unique_error_message(self, model_class, unique_check):
        """Constraints can have a custom violation error message set with the
        parameter `violation_error_message`. However, it appears that this is
        not possible for UniqueConstraint, which, for backward compatibility
        reasons (django 4.1), ignores this parameter and instead calls
        unique_error_message.

        See https://github.com/django/django/blob/69069a443a906dd4060a8047e683657d40b4c383/django/db/models/constraints.py#L356
        """
        return self.UNIQUE_ERROR_MSG

    number = models.CharField(
        max_length=255,
        null=False,
        blank=False,
        verbose_name="Numéro de l'ADS",
        help_text="Le numéro est librement fixé par chaque autorité compétente en fonction de son organisation interne.",
    )
    ads_manager = models.ForeignKey(ADSManager, on_delete=models.CASCADE)
    epci_commune = models.ForeignKey(
        Commune,
        on_delete=models.RESTRICT,
        blank=True,
        null=True,
        verbose_name="Commune de l'EPCI concernée par l'ADS",
    )

    creation_date = models.DateTimeField(auto_now_add=True, null=False)
    last_update = models.DateTimeField(auto_now=True, null=False)

    ads_creation_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Date de création initiale de l'ADS",
        help_text=mark_safe(
            "Indiquer la date à laquelle l'ADS a été attribuée à un titulaire pour la première fois."
            "<br />"
            "Pour les « anciennes ADS » <strong>entrez la date de création initiale de l'ADS</strong>, et pas la date éventuelle de cession à un nouveau titulaire."
        ),
    )

    ads_in_use = models.BooleanField(
        blank=False, null=False, verbose_name="L'ADS est-elle actuellement exploitée ?"
    )

    ads_renew_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Date du dernier renouvellement de l'ADS",
        help_text="Les ADS créées depuis le 1er octobre 2014 sont valables 5 ans et doivent être renouvelées.",
    )

    attribution_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Date d'attribution de l'ADS au titulaire actuel",
        help_text="Laissez ce champ vide si le titulaire n'a pas changé depuis la création de l'ADS.",
    )

    accepted_cpam = models.BooleanField(
        blank=True, null=True, verbose_name="Véhicule conventionné CPAM ?"
    )

    immatriculation_plate = models.CharField(
        max_length=128, null=False, blank=True, verbose_name="Plaque d'immatriculation"
    )

    vehicle_compatible_pmr = models.BooleanField(
        blank=True,
        null=True,
        verbose_name="Véhicule compatible PMR ?",
        help_text=(
            "Vous pouvez retrouver cette information sur la mention « J.3 : "
            "handicap » de la carte grise du véhicule concerné par l'ADS."
        ),
    )

    eco_vehicle = models.BooleanField(
        blank=True,
        null=True,
        verbose_name="Véhicule électrique ou hybride ?",
        help_text=mark_safe(
            "Vous pouvez retrouver cette information sur la mention P.3 de la "
            "carte grise du véhicule concerné par l'ADS. L'ensemble des "
            "abréviations est disponible sur legifrance : <a "
            'href="https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000044084721" '
            'target="_blank">https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000044084721</a> '
        ),
    )

    owner_name = models.CharField(
        max_length=1024,
        blank=True,
        null=False,
        verbose_name="Titulaire de l'ADS",
        help_text=(
            "Pour les nouvelles ADS, précisez le nom et le prénom du titulaire de l'ADS. "
            "Pour les anciennes ADS, précisez le nom et le prénom du titulaire "
            "de l'ADS s'il s'agit d'une personne physique, sinon indiquez la "
            "raison sociale de la personne morale."
        ),
    )

    owner_siret = models.CharField(
        max_length=128,
        blank=True,
        null=False,
        verbose_name="SIRET du titulaire de l'ADS",
        help_text=(
            "Nous validons ce numéro en consultant les données officielles de "
            "l'INSEE. Indiquez le numéro de SIRET (14 chiffres) sans espace. "
        ),
    )

    owner_phone = models.CharField(
        max_length=128,
        blank=True,
        null=False,
        verbose_name="Téléphone fixe du titulaire de l'ADS",
    )
    owner_mobile = models.CharField(
        max_length=128,
        blank=True,
        null=False,
        verbose_name="Téléphone mobile du titulaire de l'ADS",
    )
    owner_email = models.CharField(
        max_length=128,
        blank=True,
        null=False,
        verbose_name="Email du titulaire de l'ADS",
    )

    notes = models.TextField(
        blank=True,
        null=False,
        verbose_name="Notes sur l'ADS",
        help_text=(
            "Champ libre pour les informations complémentaires utiles (numéro d'enregistrement dans le registre des transactions, informations importantes concernant la délivrance ou la cession de l'ADS, etc…)"
        ),
    )


def get_legal_filename(instance, filename):
    now = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    filename = os.path.basename(filename)
    name = "/".join(
        [
            "%s %s - %s"
            % (
                instance.ads.ads_manager.content_type.name.capitalize(),
                instance.ads.ads_manager.content_object.id,
                instance.ads.ads_manager.content_object.display_text().capitalize(),
            ),
            f"{now}_ADS_{instance.ads.id}_{filename}",
        ]
    )
    return name


@cleanup.ignore
@reversion.register
class ADSLegalFile(
    SoftDeleteMixin,
    models.Model,
):
    class Meta:
        verbose_name = "Arrêté portant sur l'attribution de l'ADS"
        verbose_name_plural = "Arrêtés portant sur l'attribution de l'ADS"

    def __str__(self):
        return f"Legal file {self.file.url} for ADS {self.ads.id}"

    def exists_in_storage(self):
        """Returns False if file has been removed from storage, either manually
        or after a database restore."""
        return self.file.storage.exists(self.file.name)

    def human_filename(self):
        """Reverse of get_legal_filename."""
        basename = os.path.basename(self.file.name)
        return re.split(r"ADS_[0-9]+_", basename)[-1]

    ads = models.ForeignKey(ADS, on_delete=models.CASCADE)
    creation_date = models.DateField(auto_now_add=True, null=False)

    file = models.FileField(
        upload_to=get_legal_filename,
        blank=False,
        null=False,
        max_length=512,
        verbose_name="Fichier",
    )


@reversion.register
class ADSUser(
    SmartValidationMixin,
    CharFieldsStripperMixin,
    SoftDeleteMixin,
    models.Model,
):
    """ "Exploitant" of an ADS.

    For ADS created before Oct 01. 2014, the person exploiting the ADS could be
    distinct from the ADS owner.
    """

    class Meta:
        verbose_name = "Exploitant de l'ADS"
        verbose_name_plural = "Exploitants de l'ADS"
        constraints = [
            # there can be only one titulaire_exploitant for a given ADS
            models.UniqueConstraint(
                fields=("ads", "status"),
                condition=Q(status="titulaire_exploitant", deleted_at__isnull=True),
                name="only_one_titulaire_exploitant",
                violation_error_message="Il ne peut y avoir qu'un seul titulaire par ADS.",
            ),
            # name should be empty if status = 'titulaire_exploitant', because the value is expected to be provided in ADS.owner_name
            models.CheckConstraint(
                check=(
                    Q(
                        deleted_at__isnull=False,
                    )
                    | Q(
                        status="titulaire_exploitant",
                        name="",
                    )
                    | ~Q(
                        status="titulaire_exploitant",
                    )
                ),
                name="name_empty_for_titulaire_exploitant",
                violation_error_message="Le nom du conducteur ne peut être renseigné que s'il ne s'agit pas du titulaire de l'ADS.",
            ),
            # SIRET should be empty if status = 'titulaire_exploitant', because the value is expected to be provided in ADS.owner_siret
            models.CheckConstraint(
                check=(
                    Q(
                        deleted_at__isnull=False,
                    )
                    | Q(
                        status="titulaire_exploitant",
                        siret="",
                    )
                    | ~Q(
                        status="titulaire_exploitant",
                    )
                ),
                name="siret_empty_for_titulaire_exploitant",
                violation_error_message="Le SIRET du conducteur ne peut pas être renseigné pour le titulaire de l'ADS.",
            ),
            # SIRET should be empty if status = 'legal_representative', because the value is expected to be provided in ADS.owner_siret
            models.CheckConstraint(
                check=(
                    Q(
                        deleted_at__isnull=False,
                    )
                    | Q(
                        status="legal_representative",
                        siret="",
                    )
                    | ~Q(
                        status="legal_representative",
                    )
                ),
                name="siret_empty_for_legal_representative",
                violation_error_message="Le SIRET du conducteur ne peut pas être renseigné pour le représentant légal de la société.",
            ),
            # SIRET should be empty if status = 'salarie', because employees don't have a SIRET number
            models.CheckConstraint(
                check=(
                    Q(
                        deleted_at__isnull=False,
                    )
                    | Q(
                        status="salarie",
                        siret="",
                    )
                    | ~Q(
                        status="salarie",
                    )
                ),
                name="siret_empty_for_salarie",
                violation_error_message="Le SIRET du conducteur ne peut pas être renseigné pour un salarié.",
            ),
            # date_location_gerance can only be set for locataire_gerant
            models.CheckConstraint(
                check=Q(date_location_gerance__isnull=True)
                | Q(date_location_gerance__isnull=False, status="locataire_gerant"),
                name="ads_location_gerance_set_only_for_locataire_gerant",
                violation_error_message="La date du contrat de location-gérance ne peut être renseignée que pour un locataire-gérant.",
            ),
        ]

    def __str__(self):
        return f"{self.name}"

    def save(self, *args, **kwargs):
        if (
            not self.deleted_at
            and self.ads.ads_creation_date
            and self.ads.ads_creation_date >= date(2014, 10, 1)
        ):
            existing_users = ADSUser.objects.filter(ads=self.ads).exclude(pk=self.pk)
            if existing_users.exists():
                raise ValidationError(
                    "Un seul exploitant peut être déclaré pour une ADS créée après le 1er octobre 2014."
                )
            if self.status != "titulaire_exploitant":
                raise ValidationError(
                    "Le conducteur doit nécessairement être le titulaire de l'ADS (personne physique) pour une ADS créée après le 1er octobre 2014."
                )
        return super().save(*args, **kwargs)

    ads = models.ForeignKey(ADS, on_delete=models.CASCADE)

    SMART_VALIDATION_WATCHED_FIELDS = {
        "siret": lambda _, siret: validate_siret(siret),
    }

    ADS_USER_STATUS = [
        (
            "titulaire_exploitant",
            "Le titulaire de l'ADS (personne physique)",
        ),
        (
            "legal_representative",
            "Le représentant légal de la société titulaire de l'ADS (gérant ou président non salarié)",
        ),
        (
            "salarie",
            "Salarié du titulaire de l'ADS",
        ),
        (
            "cooperateur",
            "Le locataire-coopérateur de l'ADS",
        ),
        (
            "locataire_gerant",
            "Le locataire-gérant de l'ADS",
        ),
    ]

    status = models.CharField(
        max_length=255,
        choices=ADS_USER_STATUS,
        blank=True,
        null=False,
        verbose_name="Qui est le conducteur du taxi ?",
    )
    name = models.CharField(
        max_length=1024,
        blank=True,
        null=False,
        verbose_name="Nom du conducteur",
    )
    siret = models.CharField(
        max_length=128,
        blank=True,
        null=False,
        verbose_name="SIRET de l'exploitant de l'ADS",
        help_text=(
            "Nous validons ce numéro en consultant les données officielles de "
            "l'INSEE. Indiquez le numéro de SIRET (14 chiffres) sans espace. "
        ),
    )
    license_number = models.CharField(
        max_length=64,
        blank=True,
        null=False,
        verbose_name="Numéro de la carte professionnelle",
    )
    date_location_gerance = models.DateField(
        blank=True,
        null=True,
        verbose_name="Date du contrat de location-gérance",
    )


class ADSUpdateFile(models.Model):
    """The Préfecture de Police de Paris has a custom software to manage >20 000
    ADS. To send us updates, they upload a document on a weekly basis.
    """

    class Meta:
        verbose_name = "Fichier de mise à jour d'ADS"
        verbose_name_plural = "Fichiers de mise à jour d'ADS"

    def __str__(self):
        return f"Update file from user {self.user.id} on {self.creation_date}, imported={self.imported}"

    def get_update_filename(self, filename):
        now = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        filename = os.path.basename(filename)
        name = "/".join(
            [
                "ADS_UPDATES",
                "%s - %s"
                % (
                    self.user.id,
                    self.user.email,
                ),
                f"{now} - {filename}",
            ]
        )
        return name

    creation_date = models.DateTimeField(
        auto_now_add=True, null=False, verbose_name="Date de création du fichier"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=False, blank=False
    )

    update_file = models.FileField(upload_to=get_update_filename, blank=False)

    imported = models.BooleanField(
        blank=False,
        null=False,
        default=False,
        verbose_name="Fichier importé dans notre base de données ?",
    )

    import_output = models.TextField(
        blank=True, null=False, verbose_name="Output du script d'import du fichier"
    )


class Notification(models.Model):
    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"Notifications pour l'utilisateur {self.user.email}"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="Utilisateur",
    )

    ads_manager_requests = models.BooleanField(
        default=True,
        null=False,
        verbose_name="Recevoir une notification lorsqu'une demande pour devenir gestionnaire ADS est créée (pour les préfectures uniquement)",
    )

    ads_created_or_updated = models.BooleanField(
        default=False,
        null=False,
        verbose_name="Recevoir une notification lorsqu'une ADS d'une administration gérée est créée ou modifiée (pour les préfectures uniquement)",
    )
