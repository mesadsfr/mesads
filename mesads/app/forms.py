from django.contrib.contenttypes.models import ContentType
from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.urls import reverse

from dal import autocomplete

from mesads.fradm.forms import FrenchAdministrationForm
from mesads.fradm.models import Commune

from .models import ADS, ADSLegalFile, ADSManager, ADSUser


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
            'ads_type',
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
        )

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
        label='Commune',
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
        for key in set(form.fields.keys()) - set(['ads', 'id', 'DELETE']):
            if form.cleaned_data.get(key):
                return super()._should_delete_form(form)
        return True


ADSUserFormSet = inlineformset_factory(
    ADS, ADSUser, fields=('status', 'name', 'siret', 'license_number'),
    can_delete=True, extra=10, max_num=10,
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
