from django import forms

from .models import Proprietaire


class ProprietaireForm(forms.ModelForm):
    class Meta:
        model = Proprietaire
        fields = (
            "nom",
            "siret",
            "telephone",
            "email",
        )
