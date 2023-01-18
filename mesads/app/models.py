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

    :param administrator: administration responsible to accept or deny ADSManagerRequest related to this object.

    :param content_object: ForeignKey to fradm.models.

    :param no_ads_declared: If True, the ADSManager has declared that it does not manage ADS.
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
        help_text='Cocher cette case si le gestionnaire ne gère aucune ADS.'
    )

    is_locked = models.BooleanField(
        default=False,
        help_text="Cochez cette case pour empêcher la gestion manuelle des ADS pour cette administration"
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

    :param creation_date: Creation date of the object in database.

    :param last_update: Last modification date of the object in database.

    :param number: ADS number. It is specified by the ADSManager. It is usually
        a number, but it doesn't have to be.

    :param ads_manager: Administration managing this ADS.

    :param epci_commune: If ads_manager is an EPCI, this is the Commune for
        which the ADS is registered.

    :param ads_creation_date: Initial creation date of the ADS.

    :param attribution_date: Date when the ADS has been attributed to the
      current owner.

    :param attribution_type: 'free', 'paid' or 'other' depending on how the
        current owner obtained the ADS.

    :param transaction_identifier: Identifier of the transaction in the
        "registre des transactions".

    :param attribution_reason: Explains how the ADS has been attributed when
        attribution_type is "other".

    :param accepted_cpam: Boolean, if the taxi is "conventionné par l'assurance
        maladie". NULL if unknown.

    :param immatriculation_plate: Immatriculation plate of the vehicle using
        the ADS.

    :param vehicle_compatible_pmr: Boolean set to True when the vehicle is
        compatible with PMR: Personne à Mobilité Réduite. NULL if unknown.

    :param eco_vehicle: Boolean set to True when the vehicle is electric or
        hybrid. NULL if unknown.

    :param owner_name: Name of the ADS owner. When the owner is a
        company, name the legal representative of the company.

    :param owner_siret: SIRET of the ADS owner.

    :param owner_phone: Fixed phone of the ADS owner.

    :param owner_mobile: Mobile phone of the ADS owner.

    :param owner_email: Email of the ADS owner.

    :param used_by_owner: True if the ADS is used by the owner. NULL if
        unknown.
    """
    class Meta:
        verbose_name = 'ADS'
        verbose_name_plural = 'ADS'
        constraints = [
            models.UniqueConstraint(fields=['number', 'ads_manager_id'], name='unique_ads_number')
        ]

    SMART_VALIDATION_WATCHED_FIELDS = {
        'owner_siret': lambda _, siret: validate_siret(siret),
    }

    def __str__(self):
        return f'ADS {self.id}'

    UNIQUE_ERROR_MSG = "Une ADS avec ce numéro existe déjà. Supprimez l'ADS existante, ou utilisez un autre numéro."

    def validate_unique(self, exclude=None):
        """validate_unique() is called when a ModelForm instance calls validate_unique, when the object is updated."""
        try:
            return super().validate_unique(exclude=exclude)
        except ValidationError:
            raise ValidationError({'number': self.UNIQUE_ERROR_MSG})

    number = models.CharField(max_length=255, null=False, blank=False)
    ads_manager = models.ForeignKey(ADSManager, on_delete=models.CASCADE)
    epci_commune = models.ForeignKey(Commune, on_delete=models.RESTRICT, blank=True, null=True)

    creation_date = models.DateField(auto_now_add=True, null=False)
    last_update = models.DateField(auto_now=True, null=False)

    ads_creation_date = models.DateField(blank=True, null=True)

    attribution_date = models.DateField(blank=True, null=True)

    ATTRIBUTION_TYPES = [
        ('free', "Gratuitement (délivrée par l'autorité compétente)"),
        ('paid', "Cession à titre onéreux"),
        ('other', "Autre"),
    ]

    attribution_type = models.CharField(
        max_length=16, choices=ATTRIBUTION_TYPES, blank=True, null=False)

    transaction_identifier = models.CharField(
        max_length=64, blank=True, null=False
    )

    attribution_reason = models.CharField(
        max_length=4096, blank=True, null=False)

    accepted_cpam = models.BooleanField(blank=True, null=True)

    immatriculation_plate = models.CharField(
        max_length=128, null=False, blank=True)

    vehicle_compatible_pmr = models.BooleanField(blank=True, null=True)

    eco_vehicle = models.BooleanField(blank=True, null=True)

    owner_name = models.CharField(max_length=1024, blank=True, null=False)

    owner_siret = models.CharField(max_length=128, blank=True, null=False)

    owner_phone = models.CharField(max_length=128, blank=True, null=False)
    owner_mobile = models.CharField(max_length=128, blank=True, null=False)
    owner_email = models.CharField(max_length=128, blank=True, null=False)

    used_by_owner = models.BooleanField(blank=True, null=True)


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

    ADS created before 2014 are allowed to be used by another person than it's owner.

    :param status: Status of ADS user.

    :param user_name: Firstname and lastname of the person using the ADS, or
        "raison sociale".

    :param user_siret: SIRET of the ADS user.
    :param name: Firstname and lastname of the person using the ADS, or "raison sociale".

    :param siret: SIRET of the ADS user.

    :param license_number: "numéro de la carte professionnelle"
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

    status = models.CharField(max_length=255, choices=ADS_USER_STATUS, blank=True, null=False)
    name = models.CharField(max_length=1024, blank=True, null=False)
    siret = models.CharField(max_length=128, blank=True, null=False)
    license_number = models.CharField(max_length=64, blank=True, null=True)


class ADSUpdateFile(models.Model):
    """The Préfecture de Police de Paris has a custom software to manage >20 000
    ADS. To send us updates, they upload a document on a weekly basis.

    :param creation_date: when the file was uploaded.

    :param user: user uploading the document. Should always be the user related to
        Préfecture de Police de Paris.

    :param update_file: the file containing ADS.

    :param imported: boolean to track if the file has been imported by an
        asynchronous job.
    """

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

    creation_date = models.DateTimeField(auto_now_add=True, null=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        null=False, blank=False
    )

    update_file = models.FileField(upload_to=get_update_filename, blank=True)

    imported = models.BooleanField(blank=False, null=False, default=False)
