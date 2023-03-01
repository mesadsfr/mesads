from datetime import datetime
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
from django.utils.html import mark_safe

import reversion

from django_cleanup import cleanup

from mesads.fradm.models import Commune, Prefecture


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
                    raise ValidationError({
                        key: exc
                    })


def validate_no_ads_declared(ads_manager, value):
    if ads_manager.ads_set.count() > 0 and value:
        raise ValidationError(
            'Impossible de déclarer que le gestionnaire ne gère aucune ADS, puisque des ADS sont déjà déclarées.'
        )


class ADSManager(SmartValidationMixin, models.Model):
    """Authority who can register a new ADS. Either a Prefecture, a Commune or
    a EPCI.
    """
    class Meta:
        verbose_name = 'Gestionnaire ADS'
        verbose_name_plural = 'Gestionnaires ADS'
        unique_together = (
            ('content_type', 'object_id'),
        )

        # This is required, otherwise reverse relationship don't get the
        # attribute ads_count set by ADSManagerModelManager.
        base_manager_name = 'objects'

    SMART_VALIDATION_WATCHED_FIELDS = {
        'no_ads_declared': validate_no_ads_declared,
    }

    def __str__(self):
        return f'{self.content_type.name} - {self.content_object}'

    administrator = models.ForeignKey(
        'ADSManagerAdministrator',
        on_delete=models.RESTRICT,
        null=True
    )

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to=models.Q(
            app_label='fradm', model='commune'
        ) | models.Q(
            app_label='fradm', model='epci',
        ) | models.Q(
            app_label='fradm', model='prefecture',
        )
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    no_ads_declared = models.BooleanField(
        null=False,
        default=False,
        verbose_name="L'administration ne gère aucune ADS",
        help_text='Cocher cette case si le gestionnaire ne gère aucune ADS.'
    )

    is_locked = models.BooleanField(
        default=False,
        help_text="Cochez cette case pour empêcher la gestion manuelle des ADS pour cette administration"
    )


@cleanup.ignore
class ADSManagerDecree(models.Model):
    """Represents the decree that limits the number of ADS that can be created for administration."""

    def __str__(self):
        return f'Decree for ADSManager {self.ads_manager.id}'

    def get_filename(self, filename):
        now = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
        filename = os.path.basename(filename)
        name = '/'.join([
            'ads_managers_decrees',
            '%s - %s' % (
                self.ads_manager.id,
                self.ads_manager.content_object.display_text(),
            ),
            f'{now} - {filename}'
        ])
        return name

    def human_filename(self):
        """Reverse of get_legal_filename."""
        basename = os.path.basename(self.file.name)
        return ' '.join(basename.split('-')[3:])[1:]

    def exists_in_storage(self):
        """Returns False if file has been removed from storage, either manually
        or after a database restore."""
        return self.file.storage.exists(self.file.name)

    creation_date = models.DateTimeField(
        auto_now_add=True, null=False,
        verbose_name="Date de création du fichier"
    )

    ads_manager = models.ForeignKey(
        ADSManager, on_delete=models.CASCADE,
        null=False, blank=False
    )

    file = models.FileField(
        upload_to=get_filename,
        null=False, blank=False
    )


@reversion.register
class ADSManagerRequest(models.Model):
    """User request to become ADSManager. Has to be accepted by the
    administrator (ie. the prefecture) of the ADSManager.
    """

    def __str__(self):
        return f'Requete de {self.user} pour être administrateur de {self.ads_manager}'

    class Meta:
        unique_together = (
            ('user', 'ads_manager'),
        )
        verbose_name = 'Demande pour devenir gestionnaire ADS'
        verbose_name_plural = 'Demandes pour devenir gestionnaire ADS'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        null=False, blank=False
    )
    ads_manager = models.ForeignKey(
        ADSManager, on_delete=models.CASCADE,
        null=False, blank=False,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=False
    )
    accepted = models.BooleanField(
        null=True,
        default=None
    )


class ADSManagerAdministrator(models.Model):
    """Administrator with the ability to manage users of ADSManager.

    :param users: Users who can manage the list of ads_managers.

    :param ads_managers: ADSManager managed by this administrator.

    :param expected_ads_count: Number of ADSManager expected for this prefecture.
    """
    class Meta:
        verbose_name = 'Administrateur des gestionnaires ADS'
        verbose_name_plural = 'Administrateurs des gestionnaires ADS'

    def __str__(self):
        return f'Administrateur des gestionnaires de la préfecture {self.prefecture}'

    prefecture = models.OneToOneField(
        Prefecture, on_delete=models.CASCADE, null=False, blank=False)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True)
    expected_ads_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Nombre de gestionnaires ADS attendus pour cette préfecture.'
    )

    def ordered_adsmanager_set(self):
        """Function helper to get the adsmanager set order by the administration
        name."""
        return self.adsmanager_set \
            .prefetch_related('content_object', 'ads_set') \
            .order_by('commune__libelle', 'epci__name', 'prefecture__libelle')


def validate_siret(value):
    if not value:
        return

    if not re.match(r'^\d{14}$', value):
        raise ValidationError('Un SIRET doit être composé de 14 numéros')

    if not settings.INSEE_TOKEN:
        return

    try:
        resp = requests.get(
            f'https://api.insee.fr/entreprises/sirene/V3/siret/{value}',
            headers={
                'Authorization': f'Bearer {settings.INSEE_TOKEN}'
            },
            timeout=1
        )
    # INSEE API did not answer fast enough, consider the number is valid
    except requests.exceptions.Timeout:
        return

    # Ok
    if resp.status_code >= 200 and resp.status_code < 300:
        return

    if resp.status_code == 404:
        raise ValidationError('Ce numéro SIRET est invalide')

    if resp.status_code == 429:
        logging.info(f'INSEE API rate limit reached, could not verify SIRET validity {value}')
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
        if resp.status_code == 403 and 'non diffusable' in resp_json.get('header', {}).get('message', ''):
            return

    # Unknown case, log it to sentry for future investigation
    logging.error(
        'Unknown return value from INSEE API while checking for SIRET validity',
        extra={
            'insee': value,
            'resp_status_code': resp.status_code,
            'resp': resp.text,
        }
    )


@reversion.register
class ADS(SmartValidationMixin, models.Model):
    """Autorisation De Stationnement created by ADSManager.
    """
    class Meta:
        verbose_name = 'ADS'
        verbose_name_plural = 'ADS'
        constraints = [
            # To understand why we do not define violation_error_message here,
            # see the documentation of the method `unique_error_message`
            models.UniqueConstraint(
                fields=['number', 'ads_manager_id'],
                name='unique_ads_number',
            ),

            models.CheckConstraint(
                check=Q(ads_creation_date__isnull=True)
                | Q(attribution_date__isnull=True)
                | Q(ads_creation_date__lte=F('attribution_date')),
                name='ads_creation_date_before_attribution_date',
                violation_error_message="La date de création de l'ADS doit être antérieure à la date d'attribution."
            ),
        ]

    SMART_VALIDATION_WATCHED_FIELDS = {
        'owner_siret': lambda _, siret: validate_siret(siret),
    }

    def __str__(self):
        return f'ADS {self.id}'

    def save(self, *args, **kwargs):
        if self.ads_manager.is_locked:
            raise ValidationError("Il n'est pas possible d'apporter des modifications sur les ADS d'une administration verrouillée.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.ads_manager.is_locked:
            raise ValidationError("Il n'est pas possible de supprimer une ADS d'une administration verrouillée.")
        return super().delete(*args, **kwargs)

    UNIQUE_ERROR_MSG = "Une ADS avec ce numéro existe déjà. Supprimez l'ADS existante, ou utilisez un autre numéro."

    def unique_error_message(self, model_class, unique_check):
        """Constraints can have a custom violation error message set with the
        parameter `violation_error_message`. However, it appears that this is
        not possible for UniqueConstraint, which, for backward compatibility
        reasons (django 4.1), ignore this parameter and instead call
        unique_error_message.

        See https://github.com/django/django/blob/69069a443a906dd4060a8047e683657d40b4c383/django/db/models/constraints.py#L356
        """
        return self.UNIQUE_ERROR_MSG

    number = models.CharField(
        max_length=255, null=False, blank=False,
        verbose_name="Numéro de l'ADS"
    )
    ads_manager = models.ForeignKey(ADSManager, on_delete=models.CASCADE)
    epci_commune = models.ForeignKey(
        Commune, on_delete=models.RESTRICT, blank=True, null=True,
        verbose_name="Commune de l'EPCI concernée par l'ADS",
    )

    creation_date = models.DateField(auto_now_add=True, null=False)
    last_update = models.DateField(auto_now=True, null=False)

    ads_creation_date = models.DateField(
        blank=True, null=True,
        verbose_name="Date de création de l'ADS"
    )

    attribution_date = models.DateField(
        blank=True, null=True,
        verbose_name="Date d'attribution de l'ADS au titulaire actuel"
    )

    ATTRIBUTION_TYPES = [
        ('free', "Gratuitement (délivrée par l'autorité compétente)"),
        ('paid', "Cession à titre onéreux"),
        ('other', "Autre"),
    ]

    attribution_type = models.CharField(
        max_length=16, choices=ATTRIBUTION_TYPES, blank=True, null=False,
        verbose_name="Type d'attribution de l'ADS"
    )

    transaction_identifier = models.CharField(
        max_length=64, blank=True, null=False,
        verbose_name="Numéro d'identification lié au registre des transactions",
        help_text="Ne renseignez ce numéro que dans le cas où, au sein de votre commune, vous tenez un registre relatif à l'ensemble des transactions officielles. Si vous ne tenez pas un tel registre, il n'est pas nécessaire de renseigner ce champ."
    )

    attribution_reason = models.CharField(
        max_length=4096, blank=True, null=False,
        verbose_name="Raison d'attribution"
    )

    accepted_cpam = models.BooleanField(
        blank=True, null=True,
        verbose_name="Véhicule conventionné CPAM ?"
    )

    immatriculation_plate = models.CharField(
        max_length=128, null=False, blank=True,
        verbose_name="Plaque d'immatriculation"
    )

    vehicle_compatible_pmr = models.BooleanField(
        blank=True, null=True,
        verbose_name="Véhicule compatible PMR ?",
        help_text=(
            "Vous pouvez retrouver cette information sur la mention « J.3 : "
            "handicap » de la carte grise du véhicule concerné par l'ADS."
        )
    )

    eco_vehicle = models.BooleanField(
        blank=True, null=True,
        verbose_name="Véhicule électrique ou hybride ?",
        help_text=mark_safe(
            "Vous pouvez retrouver cette information sur la mention P.3 de la "
            "carte grise du véhicule concerné par l'ADS. L'ensemble des "
            "abréviations est disponible sur legifrance : <a "
            "href=\"https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000044084721\" "
            "target=\"_blank\">https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000044084721</a> "
        )
    )

    owner_name = models.CharField(
        max_length=1024, blank=True, null=False,
        verbose_name="Titulaire de l'ADS",
        help_text=(
            "S'il s'agit d'une personne physique, précisez le nom et le prénom "
            "du titulaire de l'ADS. S'il s'agit d'une personne morale, indiquez "
            "sa raison sociale. "
        )
    )

    owner_siret = models.CharField(
        max_length=128,
        blank=True, null=False,
        verbose_name="SIRET du titulaire de l'ADS",
        help_text=(
            "Nous validons ce numéro en consultant les données officielles de "
            "l'INSEE. Indiquez le numéro de SIRET (14 chiffres) sans espace. "
        )
    )

    owner_license_number = models.CharField(
        max_length=64, blank=True, null=False,
        verbose_name="Numéro de la carte professionnelle du titulaire"
    )

    owner_phone = models.CharField(
        max_length=128, blank=True, null=False,
        verbose_name="Téléphone fixe du titulaire de l'ADS"
    )
    owner_mobile = models.CharField(
        max_length=128, blank=True, null=False,
        verbose_name="Téléphone mobile du titulaire de l'ADS"
    )
    owner_email = models.CharField(
        max_length=128, blank=True, null=False,
        verbose_name="Email du titulaire de l'ADS"
    )

    used_by_owner = models.BooleanField(
        blank=True, null=True,
        verbose_name="ADS exploitée par son titulaire ?"
    )


def get_legal_filename(instance, filename):
    now = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
    filename = os.path.basename(filename)
    name = '/'.join([
        '%s %s - %s' % (
            instance.ads.ads_manager.content_type.name.capitalize(),
            instance.ads.ads_manager.content_object.id,
            instance.ads.ads_manager.content_object.display_text().capitalize()
        ),
        f'{now}_ADS_{instance.ads.id}_{filename}'
    ])
    return name


@cleanup.ignore
@reversion.register
class ADSLegalFile(models.Model):
    class Meta:
        verbose_name = "Arrêté portant sur l'attribution de l'ADS"
        verbose_name_plural = "Arrêtés portant sur l'attribution de l'ADS"

    def __str__(self):
        return f'Legal file {self.file.url} for ADS {self.ads.id}'

    def exists_in_storage(self):
        """Returns False if file has been removed from storage, either manually
        or after a database restore."""
        return self.file.storage.exists(self.file.name)

    def human_filename(self):
        """Reverse of get_legal_filename."""
        basename = os.path.basename(self.file.name)
        return re.split(r'ADS_[0-9]+_', basename)[-1]

    ads = models.ForeignKey(ADS, on_delete=models.CASCADE)
    creation_date = models.DateField(auto_now_add=True, null=False)

    file = models.FileField(upload_to=get_legal_filename, blank=False, null=False, max_length=512)


@reversion.register
class ADSUser(SmartValidationMixin, models.Model):
    """"Exploitant" of an ADS.

    For ADS created before Oct 01. 2014, the person exploiting the ADS could be
    distinct from the ADS owner.
    """

    def __str__(self):
        return f'{self.name}'

    ads = models.ForeignKey(ADS, on_delete=models.CASCADE)

    SMART_VALIDATION_WATCHED_FIELDS = {
        'siret': lambda _, siret: validate_siret(siret),
    }

    ADS_USER_STATUS = [
        ('titulaire_exploitant', 'Titulaire exploitant'),
        ('cooperateur', 'Locataire coopérateur'),
        ('locataire_gerant', 'Locataire gérant'),
        ('salarie', 'Salarié'),
        ('autre', 'Autre'),
    ]

    status = models.CharField(
        max_length=255, choices=ADS_USER_STATUS, blank=True, null=False,
        verbose_name="Statut de l'exploitant de l'ADS"
    )
    name = models.CharField(
        max_length=1024, blank=True, null=False,
        verbose_name="Nom de l'exploitant de l'ADS"
    )
    siret = models.CharField(
        max_length=128,
        blank=True, null=False,
        verbose_name="SIRET de l'exploitant de l'ADS",
        help_text=(
            "Nous validons ce numéro en consultant les données officielles de "
            "l'INSEE. Indiquez le numéro de SIRET (14 chiffres) sans espace. "
        )
    )
    license_number = models.CharField(
        max_length=64, blank=True, null=False,
        verbose_name="Numéro de la carte professionnelle"
    )


class ADSUpdateFile(models.Model):
    """The Préfecture de Police de Paris has a custom software to manage >20 000
    ADS. To send us updates, they upload a document on a weekly basis.
    """
    class Meta:
        verbose_name = 'Fichier de mise à jour d\'ADS'
        verbose_name_plural = 'Fichiers de mise à jour d\'ADS'

    def __str__(self):
        return f'Update file from user {self.user.id} on {self.creation_date}, imported={self.imported}'

    def get_update_filename(self, filename):
        now = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
        filename = os.path.basename(filename)
        name = '/'.join([
            'ADS_UPDATES',
            '%s - %s' % (
                self.user.id,
                self.user.email,
            ),
            f'{now} - {filename}'
        ])
        return name

    creation_date = models.DateTimeField(
        auto_now_add=True, null=False,
        verbose_name="Date de création du fichier")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        null=False, blank=False
    )

    update_file = models.FileField(upload_to=get_update_filename, blank=False)

    imported = models.BooleanField(
        blank=False, null=False, default=False,
        verbose_name="Fichier importé dans notre base de données ?"
    )
