from datetime import datetime

from django.conf import settings
from django.db import models


class ADSManager(models.Model):
    """Authority who can register a new ADS. Either a Prefecture, a Commune or
    a EPCI.

    :param users: Users who can register ADS for this manager.

    :param entity: ForeignKey to fradm mdoels.
    """
    class Meta:
        verbose_name = 'Gestionnaire ADS'
        verbose_name_plural = 'Gestionnaires ADS'

    def __str__(self):
        if self.departement:
            return f'{self.departement} - {self.raison_sociale}'
        return self.raison_sociale

    users = models.ManyToManyField(settings.AUTH_USER_MODEL)

    raison_sociale = models.CharField(max_length=1024, null=False, blank=True)

    type = models.CharField(max_length=255, null=False, blank=True)

    siret = models.CharField(max_length=128, blank=True, null=False)

    departement = models.CharField(max_length=16, null=False, blank=True)

    address = models.CharField(max_length=1024, null=False, blank=True)


class ADSManagerAdministrator(models.Model):
    """Administrator with the ability to manage users of ADSManager.

    :param users: Users who can manage the list of ads_managers.

    :param ads_managers: ADSManager managed by this administrator.
    """
    class Meta:
        verbose_name = 'Administrateur des gestionnaires ADS'
        verbose_name_plural = 'Administrateurs des gestionnaires ADS'

    users = models.ManyToManyField(settings.AUTH_USER_MODEL)
    ads_managers = models.ManyToManyField(ADSManager)


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

    :param owner_firstname: Firstname of the ADS owner. When the owner is a
        company, firstname of the legal representative of the company.

    :param owner_lastname: Firstname of the ADS owner. When the owner is a
        company, lastname of the legal representative of the company.

    :param owner_siret: SIRET of the ADS owner.

    :param used_by_owner: True if the ADS is used by the owner. NULL if
        unknown.

    :param user_status: Status of the person using the ADS. The ADS owner
        doesn't have to be the same person than the ADS user.

    :param user_name: Firstname and lastname of the person using the ADS, or
        "raison sociale".

    :param user_siret: SIRET of the ADS user.
    """
    class Meta:
        verbose_name = 'ADS'
        verbose_name_plural = 'ADS'


    number = models.CharField(max_length=255, null=False, blank=False)
    ads_manager = models.ForeignKey(ADSManager, on_delete=models.CASCADE)

    creation_date = models.DateField(auto_now_add=True, null=False)
    last_update = models.DateField(auto_now=True, null=False)

    ads_creation_date = models.DateField(blank=True, null=True)

    ADS_TYPES = [
        ('old', "L'ADS a été créée avant la loi du 1er Octobre 2014 : \"ancienne ADS \""),
        ('new', "L'ADS a été créée après la loi du 1er Octobre 2014 : \"nouvelle ADS \""),
    ]

    ads_type = models.CharField(max_length=16, choices=ADS_TYPES, blank=True, null=False)

    attribution_date = models.DateField(blank=True, null=True)

    ATTRIBUTION_TYPES = [
        ('free', "Gratuitement (delivrée par l'autorité compétente)"),
        ('paid', "Cession àt itre onéreux"),
        ('other', "Autre"),
    ]

    attribution_type = models.CharField(max_length=16, choices=ATTRIBUTION_TYPES, blank=True, null=False)

    attribution_reason = models.CharField(max_length=4096, blank=True, null=False)

    accepted_cpam = models.BooleanField(blank=True, null=True)

    immatriculation_plate = models.CharField(max_length=128, null=False, blank=True)

    vehicle_compatible_pmr = models.BooleanField(blank=True, null=True)

    eco_vehicle = models.BooleanField(blank=True, null=True)

    owner_firstname = models.CharField(max_length=1024, blank=True, null=False)
    owner_lastname = models.CharField(max_length=1024, blank=True, null=False)

    owner_siret = models.CharField(max_length=128, blank=True, null=False)

    used_by_owner = models.BooleanField(blank=True, null=True)

    ADS_USER_STATUS = [
        ('titulaire_exploitant', 'Titulaire exploitant'),
        ('cooperateur', 'Coopérateur'),
        ('locataire_gerance', 'Locataire gérance'),
        ('autre', 'Autre'),
    ]

    user_status = models.CharField(max_length=255, choices=ADS_USER_STATUS,
            blank=True, null=False)

    user_name = models.CharField(max_length=1024, blank=True, null=False)

    user_siret = models.CharField(max_length=128, blank=True, null=False)

    def get_legal_filename(self, filename):
        return '%s/%s_ADS-%s_%s' % (
            '%s-%s' % (self.ads_manager.id, self.ads_manager.raison_sociale),
            datetime.now().isoformat(),
            self.id,
            filename
        )

    legal_file = models.FileField(upload_to=get_legal_filename, blank=True)
