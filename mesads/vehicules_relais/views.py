import base64
from io import BytesIO

from django.contrib import messages
from django.contrib.staticfiles.finders import find
from django.db.models.functions import Cast, Replace
from django.db.models import CharField, F, IntegerField, Value
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DetailView,
    DeleteView,
    ListView,
    RedirectView,
    TemplateView,
    UpdateView,
    View,
)

from weasyprint import HTML

from reversion.views import RevisionMixin

import qrcode

from mesads.app.reversion_diff import ModelHistory

from .models import Proprietaire, Vehicule, DispositionSpecifique
from .forms import (
    ProprietaireDeleteForm,
    ProprietaireForm,
    SearchVehiculeForm,
    VehiculeCreateForm,
    VehiculeForm,
)
from mesads.utils_psql import SplitPart


class IndexView(RedirectView):
    url = reverse_lazy("vehicules-relais.search")


class SearchView(ListView):
    template_name = "pages/vehicules_relais/user_search.html"
    paginate_by = 100

    def get_form(self):
        return SearchVehiculeForm(self.request.GET)

    def get_queryset(self):
        # .order_by("numero") doesn't work because with a string ordering, 75-2 is higher than 75-100.
        # Instead we split the numero field and order by the first and second part.
        # Note the first part has to be cast to a string and not to an integer
        # because Corsica's departement number is 2A or 2B.
        qs = (
            Vehicule.objects.annotate(
                part1=Cast(SplitPart("numero", Value("-"), Value(1)), CharField()),
                part2=Cast(SplitPart("numero", Value("-"), Value(2)), IntegerField()),
                immatriculation_clean=Replace(
                    F("immatriculation"), Value("-"), Value("")
                ),
            )
            .order_by("part1", "part2")
            .select_related("proprietaire")
        )

        form = self.get_form()
        if form.is_valid():
            departement = form.cleaned_data["departement"]
            if departement:
                qs = qs.filter(departement__numero=departement.numero)
            immatriculation = form.cleaned_data["immatriculation"]
            if immatriculation:
                qs = qs.filter(
                    immatriculation_clean__icontains=immatriculation.replace("-", "")
                )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = self.get_form()

        context["form"] = form

        # If the form is valid and at least one field is not empty
        should_display_search_results = False
        if form.is_valid() and next((v for v in form.cleaned_data.values() if v), None):
            should_display_search_results = True
        context["should_display_search_results"] = should_display_search_results

        context["is_proprietaire"] = (
            self.request.user.is_authenticated
            and Proprietaire.objects.filter(users__in=[self.request.user]).exists()
        )
        return context


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
        # .order_by("numero") doesn't work because with a string ordering, 75-2 is higher than 75-100.
        # Instead we split the numero field and order by the first and second part.
        # Note the first part has to be cast to a string and not to an integer
        # because Corsica's departement number is 2A or 2B.
        return (
            Vehicule.objects.filter(proprietaire=self.kwargs["proprietaire_id"])
            .annotate(
                part1=Cast(SplitPart("numero", Value("-"), Value(1)), CharField()),
                part2=Cast(SplitPart("numero", Value("-"), Value(2)), IntegerField()),
            )
            .select_related("departement")
            .order_by("part1", "part2")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["object"] = self.kwargs["proprietaire"]
        ctx["deletable"] = self.kwargs["proprietaire"].vehicule_set.count() == 0
        return ctx


class ProprietaireDeleteView(RevisionMixin, DeleteView):
    template_name = "pages/vehicules_relais/proprietaire_confirm_delete.html"
    model = Proprietaire
    form_class = ProprietaireDeleteForm

    def get_object(self, queryset=None):
        return Proprietaire.objects.filter(id=self.kwargs["proprietaire_id"]).first()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["proprietaire"] = self.object
        return kwargs

    def get_success_url(self):
        return reverse(
            "vehicules-relais.proprietaire",
        )


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

        if ctx.get("vehicule"):
            ctx["disposition_specifique"] = DispositionSpecifique.objects.filter(
                departement=ctx["vehicule"].departement
            ).first()

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
        return get_object_or_404(
            Vehicule,
            proprietaire_id=self.kwargs["proprietaire_id"],
            numero=self.kwargs["vehicule_numero"],
        )

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


def create_qrcode_base64(data):
    qr = qrcode.QRCode(
        version=1,
        # Low error correction level.
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=4,
        border=1,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


class ProprietaireVehiculeRecepisseView(View):
    def get(
        self,
        request,
        proprietaire=None,
        proprietaire_id=None,
        vehicule_numero=None,
    ):
        vehicule = get_object_or_404(
            Vehicule,
            numero=self.kwargs["vehicule_numero"],
            proprietaire=proprietaire,
        )
        response = HttpResponse(
            content_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="récépissé-vehicule-{vehicule_numero}.pdf"'
            },
        )

        vehicule_public_url = request.build_absolute_uri(
            reverse("vehicules-relais.vehicule", kwargs={"numero": vehicule.numero})
        )

        html = render_to_string(
            "recepisse.html",
            {
                "path_logo_svg": find("images/Republique-francaise-logo.svg"),
                "path_font_marianne_regular": find(
                    "@gouvfr/fonts/Marianne-Regular.woff2"
                ),
                "path_font_marianne_bold": find("@gouvfr/fonts/Marianne-Bold.woff2"),
                "path_font_marianne_italic": find(
                    "@gouvfr/fonts/Marianne-Regular_Italic.woff2"
                ),
                "vehicule": vehicule,
                "qrcode": create_qrcode_base64(vehicule_public_url),
                "vehicule_public_url": vehicule_public_url,
            },
        )
        HTML(string=html).write_pdf(response)

        return response
