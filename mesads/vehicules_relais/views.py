from typing import Any
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import FormView, RedirectView, TemplateView

from mesads.fradm.forms import PrefectureForm
from mesads.fradm.models import Prefecture

from .models import Proprietaire, Vehicule


class IndexView(RedirectView):
    url = reverse_lazy("vehicules-relais.search")


class SearchView(FormView):
    template_name = "pages/vehicules_relais/search.html"
    form_class = PrefectureForm

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["is_proprietaire"] = (
            self.request.user.is_authenticated
            and Proprietaire.objects.filter(users__in=[self.request.user]).exists()
        )
        return ctx

    def form_valid(self, form):
        return redirect(
            reverse(
                "vehicules-relais.search.departement",
                kwargs={"departement": form.cleaned_data["prefecture"].numero},
            )
        )


class SearchDepartementView(TemplateView):
    template_name = "pages/vehicules_relais/search_departement.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["prefecture"] = get_object_or_404(Prefecture, numero=kwargs["departement"])
        ctx["vehicules"] = Vehicule.objects.filter(
            departement=ctx["prefecture"]
        ).select_related("proprietaire")
        return ctx


class VehiculeView(TemplateView):
    template_name = "pages/vehicules_relais/vehicule.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["vehicule"] = get_object_or_404(Vehicule, numero=kwargs["numero"])
        return ctx


class ProprietaireView(TemplateView):
    template_name = "pages/vehicules_relais/proprietaire.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["is_proprietaire"] = (
            self.request.user.is_authenticated
            and Proprietaire.objects.filter(users__in=[self.request.user]).exists()
        )
        return ctx


class NewProprietaireView(TemplateView):
    template_name = "pages/vehicules_relais/proprietaire-new.html"
