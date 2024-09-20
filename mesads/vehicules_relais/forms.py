from django import forms
from django.core.exceptions import ValidationError

from dal import autocomplete

from mesads.fradm.models import Commune, Prefecture

from .models import Proprietaire, Vehicule


class ProprietaireForm(forms.ModelForm):
    class Meta:
        model = Proprietaire
        fields = (
            "nom",
            "siret",
            "telephone",
            "email",
        )


class VehiculeForm(forms.ModelForm):
    class Meta:
        model = Vehicule
        fields = (
            "immatriculation",
            "modele",
            "motorisation",
            "date_mise_circulation",
            "nombre_places",
            "pmr",
            "commune_localisation",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["immatriculation"].required = True
        self.fields["modele"].required = True
        self.fields["motorisation"].required = True
        self.fields["date_mise_circulation"].required = True
        self.fields["nombre_places"].required = True
        self.fields["pmr"].required = True

    commune_localisation = forms.ModelChoiceField(
        queryset=Commune.objects,
        widget=autocomplete.ListSelect2(url="fradm.autocomplete.commune"),
        label=Vehicule.commune_localisation.field.verbose_name,
        help_text=Vehicule.commune_localisation.field.help_text,
        required=False,
    )


class VehiculeCreateForm(VehiculeForm):
    """Similar to the edit form, but with a required departement field."""

    class Meta(VehiculeForm.Meta):
        fields = VehiculeForm.Meta.fields + ("departement",)

    departement = forms.ModelChoiceField(
        queryset=Prefecture.objects,
        widget=autocomplete.ListSelect2(url="fradm.autocomplete.prefecture"),
        label=Vehicule.departement.field.verbose_name,
        help_text=Vehicule.departement.field.help_text,
        required=True,
    )


class ProprietaireDeleteForm(forms.ModelForm):
    class Meta:
        model = Proprietaire
        fields = []

    def __init__(self, proprietaire, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.proprietaire = proprietaire

    def clean(self):
        if self.proprietaire.vehicule_set.count():
            raise ValidationError(
                "Il est impossible de supprimer cet espace propriétaire, car des véhicules y sont rattachés."
            )
        return super().clean()


class SearchVehiculeForm(forms.Form):
    departement = forms.ModelChoiceField(
        queryset=Prefecture.objects,
        widget=autocomplete.ListSelect2(url="fradm.autocomplete.prefecture"),
        label=Vehicule.departement.field.verbose_name,
        help_text=Vehicule.departement.field.help_text,
        required=False,
    )

    immatriculation = forms.CharField(required=False)
