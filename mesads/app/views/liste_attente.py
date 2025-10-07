import io
import xlsxwriter
import datetime

from django.conf import settings
from django.db import IntegrityError, transaction, models
from django.db.models import Case, When, IntegerField, Q, Value
from django.db.models.functions import Replace
from django.http import HttpResponse, HttpResponseRedirect, FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, View, TemplateView
from django.urls import reverse
from django.utils import timezone
from pathlib import Path

from mesads.app.models import (
    InscriptionListeAttente,
    ADSManager,
    ADS,
    WAITING_LIST_UNIQUE_ERROR_MESSAGE,
)
from mesads.app.forms import (
    InscriptionListeAttenteForm,
    ArchivageInscriptionListeAttenteForm,
    ContactInscriptionListeAttenteForm,
)


class ListeAttenteView(ListView):
    template_name = "pages/ads_register/liste_attente.html"
    model = InscriptionListeAttente
    paginate_by = 50
    ordering = "-date_depot_inscription"
    context_object_name = "inscriptions"

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(ads_manager__id=self.kwargs["manager_id"])
        search = self.request.GET.get("search", "").strip()
        if not search:
            return qs

        search_items = search.split(" ")
        q = Q()
        for search_item in search_items:
            q &= (
                Q(nom__icontains=search_item)
                | Q(prenom__icontains=search_item)
                | Q(numero__icontains=search_item)
            )

        return qs.filter(q).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ads_manager"] = ADSManager.objects.get(id=self.kwargs["manager_id"])
        context["search"] = self.request.GET.get("search", "")
        return context


class DemandeArchiveesView(ListView):
    template_name = "pages/ads_register/liste_attente_archivees.html"
    model = InscriptionListeAttente
    paginate_by = 50
    ordering = "-deleted_at"
    context_object_name = "inscriptions"

    def get_queryset(self):
        qs = InscriptionListeAttente.with_deleted.filter(
            ads_manager__id=self.kwargs["manager_id"], deleted_at__isnull=False
        )

        search = self.request.GET.get("search", "").strip()
        if not search:
            return qs

        search_items = search.split(" ")
        q = Q()
        for search_item in search_items:
            q &= (
                Q(nom__icontains=search_item)
                | Q(prenom__icontains=search_item)
                | Q(numero__icontains=search_item)
            )

        return qs.filter(q).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ads_manager"] = ADSManager.objects.get(id=self.kwargs["manager_id"])
        context["search"] = self.request.GET.get("search", "")
        return context


class AttributionListeAttenteView(ListView):
    template_name = "pages/ads_register/liste_attente_attribution.html"
    model = InscriptionListeAttente
    paginate_by = 50
    context_object_name = "inscriptions"

    def get_queryset(self):
        qs = super().get_queryset()
        all_filled = Case(
            When(
                Q(nom__isnull=False)
                & ~Q(nom="")
                & Q(prenom__isnull=False)
                & ~Q(prenom="")
                & Q(adresse__isnull=False)
                & ~Q(adresse="")
                & Q(email__isnull=False)
                & ~Q(email="")
                & Q(numero_licence__isnull=False)
                & ~Q(numero_licence="")
                & Q(numero_telephone__isnull=False)
                & ~Q(numero_telephone=""),
                then=1,
            ),
            default=0,
            output_field=IntegerField(),
        )
        qs = qs.filter(ads_manager__id=self.kwargs["manager_id"])
        qs = qs.annotate(all_filled=all_filled).order_by(
            "-all_filled", "-exploitation_ads", "date_depot_inscription"
        )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["demande_retenue"] = self.get_queryset().filter(all_filled=1).first()
        if context["demande_retenue"].status == InscriptionListeAttente.INSCRIT:
            context["form"] = ContactInscriptionListeAttenteForm
        context["ads_manager"] = ADSManager.objects.get(id=self.kwargs["manager_id"])
        return context

    def post(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        action = request.POST.get("action")
        if action == "contact":
            form = ContactInscriptionListeAttenteForm(request.POST)
            inscription = InscriptionListeAttente.objects.get(
                id=request.POST.get("inscription_id")
            )
            if form.is_valid():
                data = form.cleaned_data
                inscription.date_contact = data.get("date_contact")
                inscription.delai_reponse = data.get("delai_reponse")
                inscription.status = InscriptionListeAttente.ATTENTE_REPONSE
                inscription.save()
                return HttpResponseRedirect(
                    redirect_to=reverse(
                        "app.liste_attente_attribution",
                        kwargs={"manager_id": kwargs.get("manager_id")},
                    )
                )
            else:
                context = self.get_context_data(**kwargs)
                context["form"] = form
                return self.render_to_response(context)
        if action == "validation_reponse":
            inscription = InscriptionListeAttente.objects.get(
                id=request.POST.get("inscription_id")
            )
            inscription.status = InscriptionListeAttente.REPONSE_OK
            inscription.save()
            return HttpResponseRedirect(
                redirect_to=reverse(
                    "app.liste_attente_attribution",
                    kwargs={"manager_id": kwargs.get("manager_id")},
                )
            )

        return self.render_to_response(self.get_context_data(**kwargs))


class AttributionADSInscriptionListeAttenteView(TemplateView):
    template_name = "pages/ads_register/liste_attente_attribution_choix_ads.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ads_manager = ADSManager.objects.get(id=self.kwargs["manager_id"])
        context["ads_manager"] = ads_manager
        inscription = InscriptionListeAttente.objects.get(
            id=self.kwargs["inscription_id"]
        )

        context["inscription"] = inscription

        ads_disponibles = ADS.objects.filter(
            ads_manager=ads_manager,
            ads_creation_date__gte=datetime.date(2014, 10, 1),
        )

        search = self.request.GET.get("search", "").strip()
        if search:
            search_items = search.split(" ")
            ads_disponibles = ads_disponibles.annotate(
                clean_immatriculation_plate=Replace(
                    "immatriculation_plate", Value("-"), Value("")
                )
            )
            q = Q()
            for search_item in search_items:
                q &= (
                    Q(owner_siret__icontains=search_item)
                    | Q(owner_name__icontains=search_item)
                    | Q(clean_immatriculation_plate__icontains=search_item)
                    | Q(epci_commune__libelle__icontains=search_item)
                    | Q(number__icontains=search_item)
                )
            ads_disponibles = ads_disponibles.filter(q)
            context["search"] = search
        context["ads_disponibles"] = ads_disponibles
        return context


class CreationInscriptionListeAttenteView(CreateView):
    template_name = "pages/ads_register/inscription_liste_attente.html"
    form_class = InscriptionListeAttenteForm

    def get_success_url(self):
        return reverse(
            "app.liste_attente",
            kwargs={
                "manager_id": self.kwargs["manager_id"],
            },
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ads_manager"] = ADSManager.objects.get(id=self.kwargs["manager_id"])
        return context

    def form_valid(self, form):
        ads_manager = ADSManager.objects.get(id=self.kwargs["manager_id"])
        form.instance.ads_manager = ads_manager

        # CreateView doesn't call validate_constraints(). The try/catch below
        # attemps to save the object. If IntegrityError is returned from
        # database, we return a custom error message for "number".

        try:
            with transaction.atomic():
                return super().form_valid(form)
        except IntegrityError:
            form.add_error("numero", WAITING_LIST_UNIQUE_ERROR_MESSAGE)
            return super().form_invalid(form)


class ModificationInscriptionListeAttenteView(UpdateView):
    template_name = "pages/ads_register/inscription_liste_attente.html"
    form_class = InscriptionListeAttenteForm
    pk_url_kwarg = "inscription_id"
    model = InscriptionListeAttente

    def dispatch(self, request, *args, **kwargs):
        if self.get_object().ads_manager.id != self.kwargs["manager_id"]:
            return HttpResponseRedirect(
                redirect_to=reverse(
                    "app.liste_attente_inscription_update",
                    kwargs={
                        "manager_id": self.get_object().ads_manager.id,
                        "inscription_id": self.get_object().id,
                    },
                )
            )

        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse(
            "app.liste_attente",
            kwargs={
                "manager_id": self.kwargs["manager_id"],
            },
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ads_manager"] = ADSManager.objects.get(id=self.kwargs["manager_id"])
        return context

    def form_valid(self, form):
        # CreateView doesn't call validate_constraints(). The try/catch below
        # attemps to save the object. If IntegrityError is returned from
        # database, we return a custom error message for "number".

        try:
            with transaction.atomic():
                return super().form_valid(form)
        except IntegrityError:
            form.add_error("numero", WAITING_LIST_UNIQUE_ERROR_MESSAGE)
            return super().form_invalid(form)


class ArchivageInscriptionListeAttenteView(UpdateView):
    template_name = "pages/ads_register/archivage_inscription_liste_attente.html"
    form_class = ArchivageInscriptionListeAttenteForm
    pk_url_kwarg = "inscription_id"
    model = InscriptionListeAttente

    def dispatch(self, request, *args, **kwargs):
        if self.get_object().ads_manager.id != self.kwargs["manager_id"]:
            return HttpResponseRedirect(
                redirect_to=reverse(
                    "app.liste_attente_inscription_archivage",
                    kwargs={
                        "manager_id": self.get_object().ads_manager.id,
                        "inscription_id": self.get_object().id,
                    },
                )
            )

        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse(
            "app.liste_attente_inscription_archivage_confirmation",
            kwargs={
                "manager_id": self.kwargs["manager_id"],
            },
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ads_manager"] = ADSManager.objects.get(id=self.kwargs["manager_id"])
        return context

    def form_valid(self, form):
        inscription = form.save(commit=False)
        inscription.delete()
        return HttpResponseRedirect(self.get_success_url())


class ModeleCourrierArchivageView(View):
    def get(self, request, *args, **kwargs):
        file_path = (
            Path(settings.BASE_DIR)
            / "mesads"
            / "docs"
            / "courrier_archive_liste_attente.docx"
        )
        if not file_path.exists():
            raise Http404("Fichier introuvable")
        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename="Courrier d'archivage liste d'attente.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


class ModeleCourrierContactView(View):
    def get(self, request, *args, **kwargs):
        file_path = (
            Path(settings.BASE_DIR) / "mesads" / "docs" / "courrier_contact.docx"
        )
        if not file_path.exists():
            raise Http404("Fichier introuvable")
        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename="Courrier d'acceptation d'une demande et délivrance d'une ADS - liste d'attente.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


class ArchivageConfirmationView(TemplateView):
    template_name = (
        "pages/ads_register/archivage_confirmation_inscription_liste_attente.html"
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ads_manager"] = ADSManager.objects.get(id=self.kwargs["manager_id"])
        return context


class ExportCSVInscriptionListeAttenteView(View):
    fields = [
        "numero",
        "nom",
        "prenom",
        "numero_licence",
        "numero_telephone",
        "email",
        "adresse",
        "date_depot_inscription",
        "date_dernier_renouvellement",
        "date_fin_validite",
        "commentaire",
        "exploitation_ads",
    ]

    headers = [
        "Numero",
        "Nom",
        "Prénom",
        "Numéro de carte professionnelle",
        "Numéro de téléphone",
        "Email",
        "Adresse",
        "Date de dépot d'inscription",
        "Date de dernier renouvellement",
        "Date de fin de validité",
        "Commentaire",
        "A exploité une ADS au cours des 5 dernières années",
    ]

    def _excell_cell_value(self, field_name, value):
        if value is None:
            return "", "text"

        field = InscriptionListeAttente._meta.get_field(field_name)

        # Booléen
        if isinstance(field, models.BooleanField):
            # gère True/False/None (si null=True)
            return "Oui" if value else "Non", "text"

        # Dates
        if isinstance(field, models.DateField):
            # DateField ou DateTimeField (DateTimeField hérite de DateField)
            # si c'est un DateTimeField, on peut convertir en localtime puis ne garder que la date
            return value, "date"

        # Autres types -> string standard
        return value, "auto"

    def _write_xlsx(self, inscriptions):
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {"in_memory": True})
        ws = wb.add_worksheet("Inscriptions")

        format_header = wb.add_format({"bold": True, "text_wrap": False})
        format_date = wb.add_format({"num_format": "dd/mm/yyyy"})
        format_text = wb.add_format({})

        for col, h in enumerate(self.headers):
            ws.write(0, col, h, format_header)

        ws.freeze_panes(1, 0)
        ws.autofilter(0, 0, 0, len(self.headers) - 1)

        # Suivi de largeur max par colonne
        max_width = [len(str(h)) for h in self.headers]

        row_index = 1

        for inscription in inscriptions:
            for col, field_name in enumerate(self.fields):
                raw_value = getattr(inscription, field_name)
                value, kind = self._excell_cell_value(field_name, raw_value)

                if kind == "date":
                    ws.write_datetime(row_index, col, value, format_date)
                    display_len = 10
                else:
                    ws.write_string(row_index, col, str(value), format_text)
                    display_len = len(str(value))

                if display_len > max_width[col]:
                    max_width[col] = display_len
            row_index += 1

        for col, w in enumerate(max_width):
            ws.set_column(col, col, min(w + 2, 60))

        wb.close()
        output.seek(0)
        return output

    def get(self, request, *args, **kwargs):
        ads_manager = get_object_or_404(ADSManager, id=self.kwargs.get("manager_id"))
        inscriptions = InscriptionListeAttente.objects.filter(
            ads_manager=ads_manager
        ).order_by("-date_depot_inscription")

        output = self._write_xlsx(inscriptions)
        filename = f"liste_attente_{ads_manager.content_object.display_text().replace(' ', '_')}_{timezone.now().strftime('%d_%m%Y')}"
        response = HttpResponse(
            output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response
