from django import forms
from django.core.exceptions import ValidationError

from dal import autocomplete

from .models import Commune, EPCI, Prefecture


class FrenchAdministrationForm(forms.Form):
    """Form to select a Commune, EPCI or Prefecture."""

    commune = forms.ModelChoiceField(
        queryset=Commune.objects,
        widget=autocomplete.ListSelect2(
            url="fradm.autocomplete.commune",
            attrs={
                "data-placeholder": "Sélectionnez une commune",
            },
        ),
        label="Commune",
        required=False,
    )

    epci = forms.ModelChoiceField(
        queryset=EPCI.objects,
        widget=autocomplete.ListSelect2(
            url="fradm.autocomplete.epci",
            attrs={
                "data-placeholder": "Sélectionnez un EPCI",
            },
        ),
        required=False,
        label="EPCI",
    )

    prefecture = forms.ModelChoiceField(
        queryset=Prefecture.objects,
        widget=autocomplete.ListSelect2(
            url="fradm.autocomplete.prefecture",
            attrs={
                "data-placeholder": "Sélectionnez une préfecture",
            },
        ),
        label="Préfecture",
        required=False,
    )

    def clean(self):
        cleaned_data = super().clean()
        not_none = {
            k: v
            for k, v in (
                ("epci", cleaned_data.get("epci")),
                ("prefecture", cleaned_data.get("prefecture")),
                ("commune", cleaned_data.get("commune")),
            )
            if v
        }

        if len(not_none) == 0:
            raise ValidationError(
                "Sélectionnez une commune, une EPCI ou une préfecture"
            )
        elif len(not_none) > 1:
            raise ValidationError("Veuillez sélectionner UN SEUL des champs")


class PrefectureForm(forms.Form):
    """Form to select a Prefecture."""

    prefecture = forms.ModelChoiceField(
        queryset=Prefecture.objects,
        widget=autocomplete.ListSelect2(url="fradm.autocomplete.prefecture"),
        label="Préfecture",
        required=True,
    )
