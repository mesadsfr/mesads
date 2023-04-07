from datetime import datetime
import re

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.urls import reverse

from dal import autocomplete

from mesads.fradm.forms import FrenchAdministrationForm
from mesads.fradm.models import Commune

from .models import (
    ADS,
    ADSLegalFile,
    ADSManager,
    ADSManagerDecree,
    ADSUser,
)
from .widgets import BooleanSelect


class ADSManagerForm(FrenchAdministrationForm):
    """Form to retrieve an ADSManager.

    The base class FrenchAdministrationForm displays three fields to select
    either an EPCI, a Commune or a Prefecture, and allows to select only one of
    them.

    This class sets the field ads_manager to the selected choice.
    """

    def clean(self):
        # super() method ensures only one field is set
        super().clean()

        obj = list({k: v for k, v in self.cleaned_data.items() if v}.values())[0]

        content_type = ContentType.objects.get_for_model(obj)
        manager = ADSManager.objects.get(
            content_type=content_type,
            object_id=obj.id
        )

        self.cleaned_data['ads_manager'] = manager


class ADSManagerEditForm(forms.ModelForm):
    class Meta:
        model = ADSManager
        fields = (
            'no_ads_declared',
        )


class ADSForm(forms.ModelForm):
    """Form to edit or create an instance of ADS. If :param epci: is set, the
    field epci_commune is initialized to render an autocomplete field.

    INSEE provides a list of all the communes insides EPCIs and we should
    ideally only autocomplete with these communes. However, since we haven't
    imported this list yet, we only limit to all the communes inside the same
    departement."""
    class Meta:
        model = ADS
        fields = (
            'epci_commune',
            'number',
            'ads_creation_date',
            'attribution_date',
            'attribution_type',
            'transaction_identifier',
            'attribution_reason',
            'accepted_cpam',
            'immatriculation_plate',
            'vehicle_compatible_pmr',
            'eco_vehicle',
            'owner_name',
            'owner_siret',
            'owner_phone',
            'owner_mobile',
            'owner_email',
            'used_by_owner',
            'owner_license_number',
        )
        widgets = {
            # used_by_owner has null=True because the field is not set for new
            # ADS, but we don't want to allow null values for old ADS. Use a
            # BooleanSelect instead of the default NullBooleanSelect.
            # Note, we could use a checkbox instead of a select.
            'used_by_owner': BooleanSelect(),
        }

    def __init__(self, epci=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if epci:
            self.fields['epci_commune'].queryset = Commune.objects.filter(departement=epci.departement)
            self.fields['epci_commune'].widget.url = reverse(
                'fradm.autocomplete.commune',
                kwargs={'departement': epci.departement}
            )

    epci_commune = forms.ModelChoiceField(
        queryset=None,
        widget=autocomplete.ListSelect2(),
        label=ADS.epci_commune.field.verbose_name,
        help_text=ADS.epci_commune.field.help_text,
        required=False,
    )


class AutoDeleteADSUserFormSet(BaseInlineFormSet):
    """By default, to remove an entry from a formset, you need to render a
    checkbox "DELETE" that needs to be checked to remove the entry.

    Here, we override the private method _should_delete_form to ask to remove
    the entry if all the fields are empty.
    """

    def _should_delete_form(self, form):
        # If the form is invalid, cleaned_data might be empty. We do not want to
        # remove it otherwise errors won't be displayed.
        if not form.is_valid():
            return super()._should_delete_form(form)
        for key in set(form.fields.keys()) - set(['ads', 'id', 'status', 'DELETE']):
            if form.cleaned_data.get(key):
                return super()._should_delete_form(form)
        return True


ADSUserFormSet = inlineformset_factory(
    ADS, ADSUser, fields=('status', 'name', 'siret', 'license_number'),
    can_delete=True, extra=25, max_num=25,
    formset=AutoDeleteADSUserFormSet
)


ADSLegalFileFormSet = inlineformset_factory(
    ADS, ADSLegalFile, fields=('file',),
    can_delete=True, extra=10, max_num=10
)


class ADSSearchForm(forms.Form):
    q = forms.CharField(
        label="Nom du titulaire, de l'exploitant, SIRET, plaque d'immatriculation, …",
        required=False
    )

    accepted_cpam = forms.NullBooleanField(
        label='Taxi conventionné CPAM ?',
        widget=forms.Select(
            choices=(
                ('', 'Peu importe'),
                (True, 'Oui'),
                (False, 'Non'),
            ),
        ),
        required=False
    )


ADSManagerDecreeFormSet = inlineformset_factory(
    ADSManager, ADSManagerDecree, fields=('file',),
    can_delete=True, extra=5, max_num=5
)


class ADSDecreeForm(forms.Form):
    """Form to generate "arrêté portant sur l'attribution de l'ADS"."""

    def _validate_decree_number(self, value):
        """The number of an "arrêté municipal" is formed like 0000/2022. I'm not
        sure the first part always contains four digits (for numbers < 1000
        and >= 10 000), so we accept any number of digits for this part."""
        if value and not re.match(r'\d+/\d{4}$', value):
            raise ValidationError('Le champ doit être sous la forme 0000/%s' % datetime.now().strftime('%Y'))
        return value

    ###
    # General decree information
    ###
    def clean_decree_number(self):
        return self._validate_decree_number(self.cleaned_data['decree_number'])

    def clean_decree_limiting_ads_number(self):
        return self._validate_decree_number(self.cleaned_data['decree_limiting_ads_number'])

    decree_number = forms.CharField(
        label="Numéro de l'arrêté concerné",
        help_text="Au format 0000/" + datetime.now().strftime('%Y'),
        required=True
    )
    decree_creation_date = forms.DateField(
        label="Date de saisie de l'arrêté municipal",
        required=True,
    )
    decree_commune = forms.CharField(
        label="Commune concernée par l'arrêté municipal",
        required=True
    )
    decree_limiting_ads_number = forms.CharField(
        label="Numéro de l'arrêté municipal portant la limitation du nombre d'ADS sur la commune",
        help_text="Au format 0000/" + datetime.now().strftime('%Y'),
        required=True
    )
    decree_limiting_ads_date = forms.DateField(
        label="Date de saisie de l'arrêté municipal portant la limitation du nombre d'ADS sur la commune",
        required=True
    )

    ###
    # ADS Owner
    ###
    ads_owner = forms.CharField(
        label="Titulaire de l'ADS",
        required=False
    )
    ads_owner_rcs = forms.CharField(
        label="Numéro RCS de la société, titulaire de l'ADS",
        help_text="(SIREN + Mention RCS + Ville)",
        required=False,
    )

    ###
    # ADS Rental - Location Gérance
    ###
    tenant_legal_representative = forms.CharField(
        label="Identité du réprésentant légal de la société",
        required=False
    )
    tenant_signature_date = forms.CharField(
        label="Date de la signature du contrat de locataire-gérant",
        help_text="Laissez ce champ vide si l'ADS n'est pas concernée par une location gérance",
        required=False
    )
    tenant_ads_user = forms.CharField(
        label="Identité de l'exploitant de l'ADS",
        required=False
    )

    ###
    # ADS Information
    ###
    ads_end_date = forms.DateField(
        label="Date de fin de l'ADS délivré",
        required=True
    )
    ads_number = forms.CharField(
        label="Numéro de l'ADS attribué",
        required=True
    )

    ###
    # Vehicle Information
    ###
    def clean_previous_decree_number(self):
        return self._validate_decree_number(self.cleaned_data['previous_decree_number'])

    def clean_decree_number_taxi_activity(self):
        return self._validate_decree_number(self.cleaned_data['decree_number_taxi_activity'])

    vehicle_brand = forms.CharField(
        label="Marque du véhicule concerné par l'ADS",
        required=True
    )
    vehicle_model = forms.CharField(
        label="Modèle du véhicule concerné par l'ADS",
        required=True
    )
    immatriculation_plate = forms.CharField(
        label="Numéro d'immatriculation du véhicule concerné par l'ADS",
        required=True
    )
    previous_decree_number = forms.CharField(
        label="Numéro de l'arrêté concerné précédent celui en cours de promulgation",
        help_text="Au format 0000/" + datetime.now().strftime('%Y'),
        required=False
    )
    previous_decree_date = forms.DateField(
        label="Date de saisie de l'arrêté municipal précédent celui en cours de promulgation",
        required=True
    )
    decree_number_taxi_activity = forms.CharField(
        label="Numéro de l'arrêté préfectoral local relatif à l'activité de taxi",
        help_text="Au format 0000/" + datetime.now().strftime('%Y'),
        required=True
    )
