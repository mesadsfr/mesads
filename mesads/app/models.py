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
from django.db.models import Count

from mesads.fradm.models import Prefecture


class ADSManagerModelManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.annotate(ads_count=Count('ads'))
        return qs


class ADSManager(models.Model):
    """Authority who can register a new ADS. Either a Prefecture, a Commune or
    a EPCI.

    :param users: Users who can register ADS for this manager.

    :param content_object: ForeignKey to fradm mdoels.
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

    def __str__(self):
        return f'{self.content_type.name} - {self.content_object}'

    objects = ADSManagerModelManager()

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

    def get_administrators_users(self):
        """Returns the list of users which have an entry in ADSManagerAdministrator to configure this instance."""
        users = set()
        for ads_manager_administrator in self.adsmanageradministrator_set.all():
            for user in ads_manager_administrator.users.all():
                users.add(user)
        return list(users)


class ADSManagerRequestModelManager(models.Manager):
    def get_queryset(self):
        """Improve performances for pages listing ADSManagerRequest.
        """
        qs = super().get_queryset()
        qs = qs.select_related('user')
        qs = qs.prefetch_related('ads_manager__content_type')
        qs = qs.prefetch_related('ads_manager__content_object')
        return qs


class ADSManagerRequest(models.Model):
    """User request to become ADSManager. Has to be accepted by the
    administrator (ie. the prefecture) of the ADSManager.
    """
    def __str__(self):
        return f'Requete de {self.user} pour ??tre administrateur de {self.ads_manager}'

    class Meta:
        unique_together = (
            ('user', 'ads_manager'),
        )

    objects = ADSManagerRequestModelManager()

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
    """
    class Meta:
        verbose_name = 'Administrateur des gestionnaires ADS'
        verbose_name_plural = 'Administrateurs des gestionnaires ADS'

    def __str__(self):
        return f'Administrateur des gestionnaires de la pr??fecture {self.prefecture}'

    prefecture = models.OneToOneField(
        Prefecture, on_delete=models.CASCADE, null=False, blank=False)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True)
    ads_managers = models.ManyToManyField(ADSManager, blank=True)


def validate_siret(value):
    if not re.match(r'^\d{14}$', value):
        raise ValidationError('Un SIRET doit ??tre compos?? de 14 num??ros')

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
        raise ValidationError('Ce num??ro SIRET est invalide')

    # Unknown case, log it to sentry for future investigation
    logging.error(
        'Unknown return value from INSEE API while checking for SIRET validity',
        extra={
            'insee': value,
            'resp_status_code': resp.status_code,
            'resp': resp.text,
        }
    )


class ADS(models.Model):
    """Autorisation De Stationnement created by ADSManager.

    :param creation_date: Creation date of the object in database.

    :param last_update: Last modification date of the object in database.

    :param number: ADS number. It is specified by the ADSManager. It is usually
        a number, but it doesn't have to be.

    :param ads_creation_date: Initial creation date of the ADS.

    :param ads_type: "old" if created before 2014, "new" otherwise.

    :param attribution_date: Date when the ADS has been attributed to the
      current owner.

    :param attribution_type: 'free', 'paid' or 'other' depending on how the
        current owner obtained the ADS.

    :param transaction_identifier: Identifier of the transaction in the
        "registre des transactions".

    :param attribution_reason: Explains how the ADS has been attributed when
        attribution_type is "other".

    :param accepted_cpam: Boolean, if the taxi is "conventionn?? par l'assurance
        maladie". NULL if unknown.

    :param immatriculation_plate: Immatriculation plate of the vehicle using
        the ADS.

    :param vehicle_compatible_pmr: Boolean set to True when the vehicle is
        compatible with PMR: Personne ?? Mobilit?? R??duite. NULL if unknown.

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

    def __str__(self):
        return f'ADS {self.id}'

    UNIQUE_ERROR_MSG = "Une ADS avec ce num??ro existe d??j??. Supprimez l'ADS existante, ou utilisez un autre num??ro."

    def validate_unique(self, exclude=None):
        """validate_unique() is called when a ModelForm instance calls validate_unique, when the object is updated."""
        try:
            return super().validate_unique(exclude=exclude)
        except ValidationError:
            raise ValidationError({'number': self.UNIQUE_ERROR_MSG})

    number = models.CharField(max_length=255, null=False, blank=False)
    ads_manager = models.ForeignKey(ADSManager, on_delete=models.CASCADE)

    creation_date = models.DateField(auto_now_add=True, null=False)
    last_update = models.DateField(auto_now=True, null=False)

    ads_creation_date = models.DateField(blank=True, null=True)

    ADS_TYPES = [
        ('old', "L'ADS a ??t?? cr????e avant la loi du 1er Octobre 2014 : \"ancienne ADS \""),
        ('new', "L'ADS a ??t?? cr????e apr??s la loi du 1er Octobre 2014 : \"nouvelle ADS \""),
    ]

    ads_type = models.CharField(
        max_length=16, choices=ADS_TYPES, blank=True, null=False)

    attribution_date = models.DateField(blank=True, null=True)

    ATTRIBUTION_TYPES = [
        ('free', "Gratuitement (d??livr??e par l'autorit?? comp??tente)"),
        ('paid', "Cession ?? titre on??reux"),
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

    owner_siret = models.CharField(max_length=128, blank=True, null=False,
                                   validators=[validate_siret])

    owner_phone = models.CharField(max_length=128, blank=True, null=False)
    owner_mobile = models.CharField(max_length=128, blank=True, null=False)
    owner_email = models.CharField(max_length=128, blank=True, null=False)

    used_by_owner = models.BooleanField(blank=True, null=True)

    def get_legal_filename(self, filename):
        now = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
        filename = os.path.basename(filename)
        name = '/'.join([
            '%s %s - %s' % (
                self.ads_manager.content_type.name.capitalize(),
                self.ads_manager.content_object.id,
                self.ads_manager.content_object.display_text().capitalize()
            ),
            f'{now}|ADS {self.id}|{filename}'
        ])
        return name

    legal_file = models.FileField(upload_to=get_legal_filename, blank=True)


class ADSUser(models.Model):
    """"Exploitant" of an ADS.

    ADS created before 2014 are allowed to be used by another person than it's owner.

    :param status: Status of ADS user.

    :param user_name: Firstname and lastname of the person using the ADS, or
        "raison sociale".

    :param user_siret: SIRET of the ADS user.
    :param name: Firstname and lastname of the person using the ADS, or "raison sociale".

    :param siret: SIRET of the ADS user.
    """
    def __str__(self):
        return f'{self.name}'

    ads = models.ForeignKey(ADS, on_delete=models.CASCADE)

    ADS_USER_STATUS = [
        ('titulaire_exploitant', 'Titulaire exploitant'),
        ('cooperateur', 'Locataire coop??rateur'),
        ('locataire_gerant', 'Locataire g??rant'),
        ('salarie', 'Salari??'),
        ('autre', 'Autre'),
    ]

    status = models.CharField(max_length=255, choices=ADS_USER_STATUS, blank=True, null=False)
    name = models.CharField(max_length=1024, blank=True, null=False)
    siret = models.CharField(max_length=128, blank=True, null=False, validators=[validate_siret])
