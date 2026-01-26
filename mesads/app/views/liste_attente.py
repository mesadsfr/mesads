import datetime
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.staticfiles import finders
from django.db import IntegrityError, transaction
from django.db.models import Case, Count, F, IntegerField, Q, Value, When
from django.http import FileResponse, Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.generic import (
    CreateView,
    ListView,
    TemplateView,
    UpdateView,
    View,
)
from weasyprint import CSS, HTML

from mesads.app.forms import (
    ArchivageInscriptionListeAttenteForm,
    AttributionADSForm,
    ContactInscriptionListeAttenteForm,
    InscriptionListeAttenteForm,
    ListesAttentePubliquesSearchForm,
    UpdateDelaiInscriptionListeAttenteForm,
)
from mesads.app.models import (
    ADS,
    WAITING_LIST_UNIQUE_ERROR_MESSAGE,
    ADSLegalFile,
    ADSManager,
    ADSUpdateLog,
    ADSUser,
    InscriptionListeAttente,
)

from ..services import get_inscriptions_data_for_excel_export
from .export import ExcelExporter


class ListeAttenteView(ListView):
    template_name = "pages/ads_register/liste_attente.html"
    model = InscriptionListeAttente
    paginate_by = 50
    ordering = ["date_depot_inscription"]
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
        qs = qs.filter(ads_manager__id=self.kwargs["manager_id"]).annotate(
            all_filled=all_filled,
            is_valid=Case(
                When(date_fin_validite__gte=datetime.date.today(), then=1),
                default=0,
                output_field=IntegerField(),
            ),
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
        context["attribution_allowed"] = (
            InscriptionListeAttente.objects.filter(
                ads_manager__id=self.kwargs["manager_id"],
                date_fin_validite__lt=datetime.date.today(),
            ).count()
            == 0
        )
        return context


class DemandeArchiveesView(ListView):
    template_name = "pages/ads_register/liste_attente_archivees.html"
    model = InscriptionListeAttente
    paginate_by = 50
    ordering = ["-deleted_at"]
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


class AttributionRedirectMixin:
    def dispatch(self, request, *args, **kwargs):
        if (
            InscriptionListeAttente.objects.filter(
                ads_manager__id=kwargs["manager_id"],
                date_fin_validite__lt=datetime.date.today(),
            ).count()
            != 0
        ):
            return HttpResponseRedirect(
                redirect_to=reverse(
                    "app.liste_attente", kwargs={"manager_id": kwargs["manager_id"]}
                )
            )
        return super().dispatch(request, *args, **kwargs)


class AttributionListeAttenteView(AttributionRedirectMixin, ListView):
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
        qs = (
            qs.annotate(
                all_filled=all_filled,
                is_valid=Case(
                    When(date_fin_validite__gte=datetime.date.today(), then=1),
                    default=0,
                    output_field=IntegerField(),
                ),
            )
            .exclude(is_valid=0)
            .order_by("date_depot_inscription")
        )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ads_manager"] = ADSManager.objects.get(id=self.kwargs["manager_id"])

        if self.request.GET.get("no_modale"):
            context["no_modale"] = True

        return context


class InscriptionTraitementListeAttenteView(TemplateView):
    template_name = "pages/ads_register/liste_attente_traitement_demande.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ads_manager = ADSManager.objects.get(id=self.kwargs["manager_id"])
        context["ads_manager"] = ads_manager
        inscription = get_object_or_404(
            InscriptionListeAttente, id=self.kwargs["inscription_id"]
        )
        context["inscription"] = inscription

        if inscription.status == InscriptionListeAttente.INSCRIT:
            context["form"] = ContactInscriptionListeAttenteForm(
                initial={"date_contact": timezone.localdate()}, instance=inscription
            )

        if inscription.status == InscriptionListeAttente.ATTENTE_REPONSE:
            context["form"] = UpdateDelaiInscriptionListeAttenteForm(
                instance=inscription
            )

        if inscription.status == InscriptionListeAttente.REPONSE_OK:
            context["form"] = AttributionADSForm(ads_manager=ads_manager)

        return context

    def get_post_redirect_url(self, inscription):
        return reverse(
            "app.liste_attente_traitement_demande",
            kwargs={
                "manager_id": self.kwargs.get("manager_id"),
                "inscription_id": inscription.id,
            },
        )

    def _response_invalid_form(self, form, **kwargs):
        context = self.get_context_data(**kwargs)
        context["form"] = form
        return self.render_to_response(context)

    def _handle_form(self, form_class, inscription, **kwargs):
        form = form_class(self.request.POST, instance=inscription)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(
                redirect_to=self.get_post_redirect_url(inscription)
            )
        else:
            return self._response_invalid_form(form, **kwargs)

    def _handle_attribution(self, inscription, **kwargs):
        form = AttributionADSForm(
            self.request.POST, self.request.FILES, ads_manager=inscription.ads_manager
        )
        if form.is_valid():
            data = form.cleaned_data
            ads = ADS.objects.create(
                number=form.cleaned_data["numero"],
                ads_manager=inscription.ads_manager,
                ads_creation_date=data["date_attribution"],
                ads_in_use=True,
                owner_name=f"{inscription.nom} {inscription.prenom}",
                owner_phone=inscription.numero_telephone,
                owner_email=inscription.email,
            )
            ADSLegalFile.objects.create(
                ads=ads,
                file=data["arrete"],
            )
            ADSUser.objects.create(
                ads=ads,
                status=ADSUser.TITULAIRE_EXPLOITANT,
                license_number=inscription.numero_licence,
            )
            ADSUpdateLog.create_for_ads(ads, self.request.user)

            inscription.motif_archivage = InscriptionListeAttente.ADS_ATTRIBUEE
            inscription.delete()

            messages.success(
                self.request,
                (
                    "L'ADS a bien été attribué. "
                    "L'inscription a la liste d'attente a été archivée."
                ),
            )

            return HttpResponseRedirect(
                redirect_to=reverse(
                    "app.ads.detail",
                    kwargs={"manager_id": inscription.ads_manager.id, "ads_id": ads.id},
                )
            )
        else:
            return self._response_invalid_form(form, **kwargs)

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        inscription = get_object_or_404(
            InscriptionListeAttente,
            id=self.kwargs["inscription_id"],
            ads_manager=self.kwargs["manager_id"],
        )

        if action == "contact":
            return self._handle_form(
                ContactInscriptionListeAttenteForm, inscription, **kwargs
            )

        elif action == "update_delai":
            return self._handle_form(
                UpdateDelaiInscriptionListeAttenteForm, inscription, **kwargs
            )

        elif action == "validation_reponse":
            inscription.status = InscriptionListeAttente.REPONSE_OK
            inscription.save()
            return HttpResponseRedirect(
                redirect_to=self.get_post_redirect_url(inscription)
            )

        elif action == "reset_demande":
            inscription.status = InscriptionListeAttente.INSCRIT
            inscription.delai_reponse = None
            inscription.date_contact = None
            inscription.save()
            return HttpResponseRedirect(
                redirect_to=reverse(
                    "app.liste_attente",
                    kwargs={"manager_id": inscription.ads_manager.id},
                )
            )

        elif action == "attribution_ads":
            return self._handle_attribution(inscription, **kwargs)

        return self.render_to_response(self.get_context_data(**kwargs))


class InscriptionListeAttenteMixin:
    """
    Mixin pour les fonctions communes entre la création/modification
    d'inscription a la liste d'attente
    """

    template_name = "pages/ads_register/liste_attente_inscription.html"
    form_class = InscriptionListeAttenteForm
    model = InscriptionListeAttente

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {"ads_manager": ADSManager.objects.get(id=self.kwargs["manager_id"])}
        )
        return kwargs

    def get_success_url(self):
        return reverse(
            "app.liste_attente",
            kwargs={
                "manager_id": self.kwargs["manager_id"],
            },
        )

    def form_invalid(self, form):
        messages.error(
            self.request,
            (
                "Le formulaire contient des erreurs. "
                "Veuillez les corriger avant de soumettre à nouveau."
            ),
        )
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ads_manager"] = ADSManager.objects.get(id=self.kwargs["manager_id"])
        return context

    def form_valid(self, form):
        # Create/UpdateView doesn't call validate_constraints(). The try/catch below
        # attemps to save the object. If IntegrityError is returned from
        # database, we return a custom error message for "number".

        try:
            with transaction.atomic():
                return super().form_valid(form)
        except IntegrityError as e:
            message = str(e)

            if "unique_waiting_list_number" in message:
                form.add_error("numero", WAITING_LIST_UNIQUE_ERROR_MESSAGE)
            return super().form_invalid(form)


class CreationInscriptionListeAttenteView(InscriptionListeAttenteMixin, CreateView):
    pass


class ModificationInscriptionListeAttenteView(InscriptionListeAttenteMixin, UpdateView):
    pk_url_kwarg = "inscription_id"

    def dispatch(self, request, *args, **kwargs):
        """
        Si le manager associé a l'inscription ne correspond pas à l'id
        du manager dans l'url, on redirige vers la bonne url
        """
        object = self.get_object()
        if object.ads_manager.id != self.kwargs["manager_id"]:
            return HttpResponseRedirect(
                redirect_to=reverse(
                    "app.liste_attente_inscription_update",
                    kwargs={
                        "manager_id": object.ads_manager.id,
                        "inscription_id": object.id,
                    },
                )
            )

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        inscriptions_with_same_licence_number = InscriptionListeAttente.objects.filter(
            numero_licence=self.object.numero_licence
        ).exclude(id=self.object.id)
        context["duplicated_licences"] = inscriptions_with_same_licence_number
        return context


class ArchivageInscriptionListeAttenteView(UpdateView):
    template_name = "pages/ads_register/liste_attente_archivage_inscription.html"
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

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Le formulaire contient des erreurs. "
            "Veuillez les corriger avant de soumettre à nouveau.",
        )
        return super().form_invalid(form)

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
        filename = (
            "Courrier d'acceptation d'une demande et délivrance d'une ADS - "
            "liste d'attente.docx"
        )
        if not file_path.exists():
            raise Http404("Fichier introuvable")
        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename=filename,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


class ArchivageConfirmationView(TemplateView):
    template_name = (
        "pages/ads_register/liste_attente_archivage_confirmation_inscription.html"
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ads_manager"] = ADSManager.objects.get(id=self.kwargs["manager_id"])
        return context


class ExportCSVInscriptionListeAttenteView(ExcelExporter, View):
    ads_manager = None

    def setup(self, request, *args, **kwargs):
        self.ads_manager = get_object_or_404(ADSManager, id=kwargs.get("manager_id"))
        return super().setup(request, *args, **kwargs)

    def get_filename(self):
        return (
            "liste_attente_"
            f"{self.ads_manager.content_object.display_text().replace(' ', '_')}"
            f"_{timezone.now().strftime('%d_%m%Y')}.xlsx"
        )

    def get_file_title(self):
        return (
            "Liste d'attente - "
            f"{self.ads_manager.content_object.display_text().capitalize()}"
        )

    def generate(self, workbook):
        headers, inscriptions = get_inscriptions_data_for_excel_export(self.ads_manager)
        self.add_sheet(
            workbook,
            "Inscriptions",
            "TableauInscriptions",
            headers,
            inscriptions,
        )


class ListesAttentesPubliquesView(ListView):
    template_name = "pages/ads_register/listes_attentes_publiques.html"
    model = ADSManager
    paginate_by = 50
    context_object_name = "ads_managers"

    def get_form(self):
        return ListesAttentePubliquesSearchForm(self.request.GET)

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .filter(liste_attente_publique=True)
            .order_by("administrator")
        )

        form = self.get_form()
        if form.is_valid():
            departement = form.cleaned_data["departement"]
            if departement:
                qs = qs.filter(administrator__prefecture=departement)
            commune = form.cleaned_data["commune"]
            if commune:
                qs = qs.annotate(
                    name_search=Case(
                        When(content_type__model="epci", then=F("epci__name")),
                        When(
                            content_type__model="prefecture",
                            then=F("prefecture__libelle"),
                        ),
                        When(content_type__model="aeroport", then=F("aeroport__name")),
                        When(content_type__model="commune", then=F("commune__libelle")),
                        default=Value(""),
                    )
                )
                qs = qs.filter(name_search__icontains=commune)

            qs = qs.annotate(
                nombre_inscriptions_liste=Count(
                    "inscriptions_liste_attente",
                    filter=Q(
                        inscriptions_liste_attente__date_fin_validite__gte=datetime.date.today(),
                        inscriptions_liste_attente__deleted_at__isnull=True,
                    ),
                )
            )

            if form.is_filled():
                return qs

        return ADSManager.objects.none()

    def get_extra_query_params(self, form):
        extra_query_params = ""
        if form.is_valid():
            if form.cleaned_data.get("departement"):
                extra_query_params = (
                    f"{extra_query_params}&"
                    f"departement={form.cleaned_data.get('departement').id}"
                )
            if form.cleaned_data.get("commune"):
                extra_query_params = (
                    f"{extra_query_params}&commune={form.cleaned_data.get('commune')}"
                )
        return extra_query_params

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = self.get_form()
        context["form"] = form
        context["extra_query_params"] = self.get_extra_query_params(form)
        return context


class ListeAttentePublique(ListView):
    template_name = "pages/ads_register/liste_attente_publique.html"
    model = InscriptionListeAttente
    paginate_by = 50
    context_object_name = "inscriptions"
    ordering = ["date_depot_inscription"]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(
            ads_manager__id=self.kwargs["manager_id"],
            date_fin_validite__gte=datetime.date.today(),
        )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ads_manager"] = get_object_or_404(
            ADSManager, id=self.kwargs["manager_id"], liste_attente_publique=True
        )
        return context


class ChangementStatutListeView(View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        ads_manager = get_object_or_404(ADSManager, id=kwargs["manager_id"])
        liste_attente_publique = self.request.POST.get("liste_attente_publique")
        ads_manager.liste_attente_publique = liste_attente_publique == "1"
        ads_manager.save()
        messages.success(
            request,
            (
                "La liste d'attente a été rendue publique"
                if ads_manager.liste_attente_publique is True
                else "La liste d'attente a été rendu privée"
            ),
        )

        return HttpResponseRedirect(
            redirect_to=reverse(
                "app.liste_attente", kwargs={"manager_id": ads_manager.id}
            )
        )


class ExportPDFListePubliqueView(View):
    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        ads_manager = get_object_or_404(ADSManager, id=kwargs["manager_id"])

        inscriptions = InscriptionListeAttente.objects.filter(
            ads_manager=ads_manager,
            date_fin_validite__gte=datetime.date.today(),
        ).order_by("date_depot_inscription")

        context = {"ads_manager": ads_manager, "inscriptions": inscriptions}

        html_string = render_to_string(
            "pages/ads_register/liste_attente_publique_pdf.html", context
        )
        filename = "liste-attente-publique.pdf"
        response = HttpResponse(
            content_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

        dsfr_css_path = finders.find("@gouvfr/dsfr/dsfr.min.css")
        stylesheets = []
        if dsfr_css_path:
            stylesheets.append(CSS(filename=dsfr_css_path))

        HTML(string=html_string).write_pdf(target=response, stylesheets=stylesheets)

        return response
