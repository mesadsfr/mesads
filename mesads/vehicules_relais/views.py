from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DetailView,
    DeleteView,
    FormView,
    ListView,
    RedirectView,
    TemplateView,
    UpdateView,
)

from reversion.views import RevisionMixin

from mesads.fradm.forms import PrefectureForm
from mesads.fradm.models import Prefecture

from mesads.app.reversion_diff import ModelHistory

from .models import Proprietaire, Vehicule
from .forms import ProprietaireForm, VehiculeForm, VehiculeCreateForm


class IndexView(RedirectView):
    url = reverse_lazy("vehicules-relais.search")


class SearchView(FormView):
    template_name = "pages/vehicules_relais/user_search.html"
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
    template_name = "pages/vehicules_relais/user_search_departement.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["prefecture"] = get_object_or_404(Prefecture, numero=kwargs["departement"])
        ctx["vehicules"] = Vehicule.objects.filter(
            departement=ctx["prefecture"]
        ).select_related("proprietaire")
        return ctx


class VehiculeView(TemplateView):
    template_name = "pages/vehicules_relais/user_vehicule.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["vehicule"] = get_object_or_404(Vehicule, numero=kwargs["numero"])
        return ctx


class ProprietaireListView(ListView):
    template_name = "pages/vehicules_relais/proprietaire_list.html"
    paginate_by = 50

    def get_queryset(self):
        return Proprietaire.objects.filter(users__in=[self.request.user]).order_by(
            "nom"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["is_proprietaire"] = (
            self.request.user.is_authenticated
            and Proprietaire.objects.filter(users__in=[self.request.user]).exists()
        )
        return ctx


class ProprietaireEditView(RevisionMixin, UpdateView):
    template_name = "pages/vehicules_relais/proprietaire_edit.html"
    model = Proprietaire
    pk_url_kwarg = "proprietaire_id"
    form_class = ProprietaireForm

    def get_success_url(self):
        return reverse(
            "vehicules-relais.proprietaire.detail",
            kwargs={"proprietaire_id": self.object.id},
        )


class ProprietaireCreateView(ProprietaireEditView, CreateView):
    template_name = "pages/vehicules_relais/proprietaire_edit.html"
    form_class = ProprietaireForm

    def get_object(self, queryset=None):
        return None

    def form_valid(self, form):
        redirection = super().form_valid(form)
        self.object.users.set([self.request.user])
        return redirection


class ProprietaireDetailView(ListView):
    template_name = "pages/vehicules_relais/proprietaire_detail.html"
    paginate_by = 50

    def get_queryset(self):
        return (
            Vehicule.objects.filter(proprietaire=self.kwargs["proprietaire_id"])
            .select_related("departement")
            .order_by(("numero"))
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["object"] = self.kwargs["proprietaire"]
        return ctx


class ProprietaireHistoryView(DetailView):
    template_name = "pages/vehicules_relais/proprietaire_history.html"
    model = Proprietaire
    pk_url_kwarg = "proprietaire_id"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["history"] = ModelHistory(
            self.object,
            ignore_fields=[
                Proprietaire._meta.get_field("created_at"),
                Proprietaire._meta.get_field("last_update_at"),
                Proprietaire._meta.get_field("users"),
                # Ignore all the changes to the vehicules.
                *[field for field in Vehicule._meta.fields],
            ],
        )
        return ctx


class ProprietaireVehiculeUpdateView(RevisionMixin, UpdateView):
    template_name = "pages/vehicules_relais/proprietaire_vehicule.html"
    form_class = VehiculeForm
    success_message = "Les modifications ont été enregistrées."

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["proprietaire"] = self.kwargs["proprietaire"]
        return ctx

    def get_object(self):
        return get_object_or_404(
            Vehicule,
            numero=self.kwargs["vehicule_numero"],
            proprietaire=self.kwargs["proprietaire_id"],
        )

    def get_success_message(self):
        return self.success_message

    def form_valid(self, form):
        ret = super().form_valid(form)
        messages.success(self.request, self.get_success_message())
        return ret

    def get_success_url(self):
        return reverse(
            "vehicules-relais.proprietaire.vehicule.edit",
            kwargs={
                "proprietaire_id": self.object.proprietaire.id,
                "vehicule_numero": self.object.numero,
            },
        )


class ProprietaireVehiculeDeleteView(RevisionMixin, DeleteView):
    template_name = "pages/vehicules_relais/proprietaire_vehicule_confirm_delete.html"
    model = Vehicule

    def get_object(self, queryset=None):
        return Vehicule.objects.filter(
            proprietaire_id=self.kwargs["proprietaire_id"],
            numero=self.kwargs["vehicule_numero"],
        ).first()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["proprietaire"] = self.kwargs["proprietaire"]
        return ctx

    def get_success_url(self):
        return reverse(
            "vehicules-relais.proprietaire.detail",
            kwargs={
                "proprietaire_id": self.kwargs["proprietaire_id"],
            },
        )


class ProprietaireVehiculeCreateView(ProprietaireVehiculeUpdateView, CreateView):
    form_class = VehiculeCreateForm

    def get_object(self, queryset=None):
        return None

    def form_valid(self, form):
        form.instance.proprietaire = self.kwargs["proprietaire"]
        return super().form_valid(form)

    def get_success_message(self):
        return f"Le véhicule a été enregistré. Le numéro <strong>{self.object.numero}</strong> lui a été attribué."


class ProprietaireVehiculeHistoryView(DetailView):
    template_name = "pages/vehicules_relais/proprietaire_vehicule_history.html"

    def get_object(self, queryset=None):
        return get_object_or_404(
            Vehicule,
            numero=self.kwargs["vehicule_numero"],
            proprietaire=self.kwargs["proprietaire_id"],
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["history"] = ModelHistory(
            self.object,
            ignore_fields=[
                Vehicule._meta.get_field("created_at"),
                Vehicule._meta.get_field("last_update_at"),
                Vehicule._meta.get_field("proprietaire"),
                Vehicule._meta.get_field("departement"),
            ],
        )
        ctx["proprietaire"] = self.kwargs["proprietaire"]
        return ctx
