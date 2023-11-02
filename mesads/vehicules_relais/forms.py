from django import forms

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
        fields = ("immatriculation",)
