from datetime import datetime
import re

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
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

        obj = list({k: v for k, v in self.cleaned_data.items() if v}.values())[0]

        content_type = ContentType.objects.get_for_model(obj)
        manager = ADSManager.objects.get(content_type=content_type, object_id=obj.id)

        self.cleaned_data["ads_manager"] = manager


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
    fields=("status", "name", "siret", "license_number", "deleted_at"),
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


class ADSDecreeForm1(forms.Form):
    STEP_TITLE = "Modèle de l'arrêté"

    is_old_ads = forms.BooleanField(
        label="Le modèle d'arrêté que vous souhaitez générer concerne-t-il une ADS antérieure au 1er Octobre 2014 ?",
        required=False,
        widget=BooleanSelect(),
    )


class ADSDecreeForm2(forms.Form):
    STEP_TITLE = "Motif d'émission de l'arrêté"

    def __init__(self, is_old_ads, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_old_ads = is_old_ads
        self.fields["decree_creation_reason"].choices = (
            self.CHOICES_REASON_OLD_ADS if is_old_ads else self.CHOICES_REASON_NEW_ADS
        )

    CHOICES_REASON_OLD_ADS = (
        (
            "rental",
            "Passage de l'ADS en location gérance ou changement de locataire-gérant",
        ),
        ("change_owner", "Changement de titulaire de l'ADS"),
        ("change_vehicle", "Changement du véhicule associé à l'ADS"),
    )

    CHOICES_REASON_NEW_ADS = (
        ("renew", "Renouvellement d'une ADS"),
        ("create", "Création d'une ADS"),
        ("change_vehicle", "Changement de véhicule associé à l'ADS"),
    )

    decree_creation_reason = forms.ChoiceField(
        label="Pour quel motif voulez-vous émettre un arrêté ?",
        required=False,
    )


class ADSDecreeForm3(forms.Form):
    """Form to generate "arrêté portant sur l'attribution de l'ADS"."""

    def __init__(self, is_old_ads, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_old_ads = is_old_ads
        if not is_old_ads:
            self.fields["ads_end_date"] = forms.DateField(
                label="Date de fin de l'ADS délivrée",
                help_text="Les ADS créées après le 1er octobre 2014 ont une durée de validité de 5 ans à compter de la date de création",
                required=False,
            )

    STEP_TITLE = "Informations générales"

    def _validate_decree_number(self, value):
        """The number of an "arrêté municipal" is formed like 0000/2022.
        Apparently, the first part can contain letters too."""
        if value and not re.match(r".+/\d{4}$", value):
            raise ValidationError(
                "Le champ doit être sous la forme XXXX/%s"
                % datetime.now().strftime("%Y")
            )
        return value

    ###
    # General decree information
    ###
    def clean_decree_number(self):
        return self._validate_decree_number(self.cleaned_data["decree_number"])

    def clean_decree_limiting_ads_number(self):
        return self._validate_decree_number(
            self.cleaned_data["decree_limiting_ads_number"]
        )

    decree_number = forms.CharField(
        label="Numéro de l'arrêté concerné",
        help_text="Au format 0000/" + datetime.now().strftime("%Y"),
        required=False,
    )
    decree_creation_date = forms.DateField(
        label="Date de saisie de l'arrêté municipal",
        required=False,
    )
    decree_commune = forms.CharField(
        label="Commune concernée par l'arrêté municipal",
        required=False,
    )
    administrative_court = forms.CharField(
        label="Tribunal administratif compétent",
        help_text="Indiquer le nom de la ville du Tribunal",
        required=False,
    )
    decree_limiting_ads_number = forms.CharField(
        label="Numéro de l'arrêté municipal portant la limitation du nombre d'ADS sur la commune",
        help_text="Au format 0000/" + datetime.now().strftime("%Y"),
        required=False,
    )
    decree_limiting_ads_date = forms.DateField(
        label="Date de saisie de l'arrêté municipal portant la limitation du nombre d'ADS sur la commune",
        required=False,
    )

    ###
    # ADS Owner
    ###
    ads_owner = forms.CharField(
        label="Titulaire de l'ADS",
        required=False,
    )
    ads_owner_rcs = forms.CharField(
        label="Numéro RCS de la société, titulaire de l'ADS",
        help_text="(SIREN + Mention RCS + Ville)",
        required=False,
    )

    ###
    # ADS Leasing - Location Gérance
    ###
    tenant_legal_representative = forms.CharField(
        label="Identité du réprésentant légal de la société",
        required=False,
    )
    tenant_signature_date = forms.CharField(
        label="Date de la signature du contrat de locataire-gérant",
        help_text="Laissez ce champ vide si l'ADS n'est pas concernée par une location gérance",
        required=False,
    )
    tenant_ads_user = forms.CharField(
        label="Identité de l'exploitant de l'ADS",
        help_text="Laissez ce champ vide si l'ADS n'est pas concernée par une location gérance",
        required=False,
    )

    ###
    # ADS Information
    ###
    ads_number = forms.CharField(
        label="Numéro de l'ADS attribuée",
        required=False,
    )

    ###
    # Vehicle Information
    ###
    def clean_previous_decree_number(self):
        return self._validate_decree_number(self.cleaned_data["previous_decree_number"])

    def clean_decree_number_taxi_activity(self):
        return self._validate_decree_number(
            self.cleaned_data["decree_number_taxi_activity"]
        )

    vehicle_brand = forms.CharField(
        label="Marque du véhicule concerné par l'ADS",
        required=False,
    )
    vehicle_model = forms.CharField(
        label="Modèle du véhicule concerné par l'ADS",
        required=False,
    )
    immatriculation_plate = forms.CharField(
        label="Numéro d'immatriculation du véhicule concerné par l'ADS",
        required=False,
    )
    previous_decree_number = forms.CharField(
        label="Numéro de l'arrêté concerné précédent celui en cours de promulgation",
        help_text=f"Au format 0000/ {datetime.now().strftime('%Y')}. Laissez ce champ vide si l'ADS ne concerne pas un renouvellement, une cession ou un changement de véhicule",
        required=False,
    )
    previous_decree_date = forms.DateField(
        label="Date de saisie de l'arrêté municipal précédent celui en cours de promulgation",
        help_text="Laissez ce champ vide si l'ADS ne concerne pas un renouvellement, une cession ou un changement de véhicule",
        required=False,
    )
    decree_number_taxi_activity = forms.CharField(
        label="Numéro de l'arrêté préfectoral local relatif à l'activité de taxi",
        help_text="Au format 0000/" + datetime.now().strftime("%Y"),
        required=False,
    )


class ADSDecreeForm4(forms.Form):
    STEP_TITLE = "Téléchargement de l'arrêté"


class ADSManagerMultipleChoiceField(forms.ModelMultipleChoiceField):
    widget = autocomplete.ModelSelect2Multiple(url="app.autocomplete.ads-manager")

    def label_from_instance(self, ads_manager):
        return ads_manager.human_name()


class ADSManagerAutocompleteForm(forms.Form):
    q = ADSManagerMultipleChoiceField(
        queryset=ADSManager.objects,
        label="Gestionnaires ADS",
        required=True,
    )
