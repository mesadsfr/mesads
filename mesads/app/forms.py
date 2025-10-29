from django.contrib.contenttypes.models import ContentType
from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.urls import reverse, reverse_lazy

from dal import autocomplete

from mesads.fradm.forms import FrenchAdministrationForm
from mesads.fradm.models import Commune, EPCI, Prefecture

from .fields import NullBooleanField
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

        obj = list(
            {
                k: v
                for k, v in (
                    ("epci", self.cleaned_data.get("epci")),
                    ("prefecture", self.cleaned_data.get("prefecture")),
                    ("commune", self.cleaned_data.get("commune")),
                )
                if v
            }.values()
        )[0]

        content_type = ContentType.objects.get_for_model(obj)
        manager = ADSManager.objects.get(content_type=content_type, object_id=obj.id)

        self.cleaned_data["ads_manager"] = manager

    is_ads_manager = forms.BooleanField(
        required=True,
        label="J'atteste être gestionnaire d'ADS au sein d'une administration (mairie, EPCI ou préfecture)",
        help_text="Ne remplissez pas ce formulaire si vous êtes chauffeur de taxi, ou si vous n'êtes pas employé par une administration.",
    )


class ADSManagerEditForm(forms.ModelForm):
    class Meta:
        model = ADSManager
        fields = (
            "no_ads_declared",
            "epci_delegate",
        )

    def __init__(self, instance=None, *args, **kwargs):
        super().__init__(instance=instance, *args, **kwargs)
        if instance.content_type.model_class() in (EPCI, Prefecture):
            self.fields["epci_delegate"].disabled = True
        elif instance.content_type.model_class() == Commune:
            self.fields["epci_delegate"].queryset = EPCI.objects.filter(
                departement=instance.content_object.departement
            )
            self.fields["epci_delegate"].widget.url = reverse(
                "fradm.autocomplete.epci",
                kwargs={"departement": instance.content_object.departement},
            )

    epci_delegate = forms.ModelChoiceField(
        queryset=None,
        widget=autocomplete.ListSelect2(url=reverse_lazy("fradm.autocomplete.epci")),
        label=ADSManager.epci_delegate.field.verbose_name,
        help_text=ADSManager.epci_delegate.field.help_text,
        required=False,
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
            "epci_commune",
            "number",
            "ads_creation_date",
            "ads_in_use",
            "ads_renew_date",
            "attribution_date",
            "accepted_cpam",
            "immatriculation_plate",
            "vehicle_compatible_pmr",
            "eco_vehicle",
            "owner_name",
            "owner_siret",
            "owner_phone",
            "owner_mobile",
            "owner_email",
            "notes",
            # It is important to leave "deleted_at" in the fields, otherwise
            # django.db.models.constraints.CheckConstraint.validate() will silently skip
            # the evaluation of the constraints using this field.
            # In other words, if deleted_at is not in the fields, saving the
            # form will not trigger the correct error message in case the unique
            # constraint is violated.
            "deleted_at",
        )

    def __init__(self, epci=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if epci:
            self.fields["epci_commune"] = forms.ModelChoiceField(
                queryset=None,
                widget=autocomplete.ListSelect2(),
                label=ADS.epci_commune.field.verbose_name,
                help_text=ADS.epci_commune.field.help_text,
                required=False,
            )
            self.fields["epci_commune"].queryset = Commune.objects.filter(
                departement=epci.departement
            )
            self.fields["epci_commune"].widget.url = reverse(
                "fradm.autocomplete.commune", kwargs={"departement": epci.departement}
            )

    def save(self, check=True):
        """More or less a copy of super().save(), but forwards `check` to the
        instance's save method."""
        self.instance.save(check=check)
        self._save_m2m()
        return self.instance

    ads_in_use = NullBooleanField(
        widget=BooleanSelect(),
        label=ADS.ads_in_use.field.verbose_name,
        help_text=ADS.ads_in_use.field.help_text,
        required=True,
    )

    certify = forms.BooleanField(
        label="Je certifie que les informations enregistrées sont à jour et ne comportent pas d'erreur de saisie.",
        required=True,
        error_messages={
            "required": "Vous devez cocher cette case pour valider le formulaire."
        },
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
        for key in set(form.fields.keys()) - set(["ads", "id", "status", "DELETE"]):
            if form.cleaned_data.get(key):
                return super()._should_delete_form(form)
        return True


ADSUserFormSet = inlineformset_factory(
    ADS,
    ADSUser,
    # It is important to leave "deleted_at" in the fields, otherwise
    # django.db.models.constraints.CheckConstraint.validate() will silently skip
    # the evaluation of the constraints using this field.
    # Does it suck? Yes. Did I spend 2 days to figure it out? Also yes.
    fields=(
        "status",
        "name",
        "siret",
        "license_number",
        "date_location_gerance",
        "deleted_at",
    ),
    can_delete=True,
    extra=0,
    formset=AutoDeleteADSUserFormSet,
)


ADSLegalFileFormSet = inlineformset_factory(
    ADS,
    ADSLegalFile,
    fields=("file",),
    can_delete=True,
    extra=0,
)


class ADSSearchForm(forms.Form):
    q = forms.CharField(
        label="Nom du titulaire, de l'exploitant, SIRET, plaque d'immatriculation, …",
        required=False,
    )

    accepted_cpam = forms.NullBooleanField(
        label="Taxi conventionné CPAM ?",
        widget=forms.Select(
            choices=(
                ("", "Peu importe"),
                (True, "Oui"),
                (False, "Non"),
            ),
        ),
        required=False,
    )


ADSManagerDecreeFormSet = inlineformset_factory(
    ADSManager,
    ADSManagerDecree,
    fields=("file",),
    can_delete=True,
    extra=0,
)


class ADSManagerMultipleChoiceField(forms.ModelMultipleChoiceField):
    widget = autocomplete.ModelSelect2Multiple(
        url="app.autocomplete.ads-manager",
        attrs={"data-placeholder": "Sélectionnez un gestionnaire ADS"},
    )

    def label_from_instance(self, ads_manager):
        return ads_manager.human_name()


class ADSManagerAutocompleteForm(forms.Form):
    q = ADSManagerMultipleChoiceField(
        queryset=ADSManager.objects,
        label="Gestionnaires ADS",
        required=False,
    )


class SearchVehiculeForm(forms.Form):
    immatriculation = forms.CharField(required=False)
