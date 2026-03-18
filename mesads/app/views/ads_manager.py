from datetime import timedelta

from dal import autocomplete
from django.contrib import messages
from django.contrib.postgres.lookups import Unaccent
from django.db.models import (
    BooleanField,
    Case,
    CharField,
    Count,
    DateTimeField,
    ExpressionWrapper,
    F,
    FloatField,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Cast, Coalesce, Now, Replace, Round
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import TemplateView, View
from django.views.generic.edit import ProcessFormView
from django.views.generic.list import ListView

from ..forms import (
    ADSManagerDecreeForm,
    ADSManagerEditForm,
)
from ..models import ADS, ADSManager, ADSManagerDecree, ADSManagerRequest, ADSUpdateLog


class AdministrationsEnGestionView(TemplateView):
    template_name = "pages/ads_register/ads_manager_administrations.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # All ADS for the manager
        ads_count_subquery = (
            ADS.objects.filter(
                ads_manager=OuterRef("ads_manager_id"),
            )
            .values("ads_manager")
            .annotate(count=Count("*"))
            .values("count")[:1]
        )

        # annotate the latest ADSUpdateLog.update_date
        latest_log_qs = ADSUpdateLog.objects.filter(ads=OuterRef("pk")).order_by(
            "-update_at"
        )

        # 2) Count how many ADS under this manager have latest_complete=True
        complete_updates_subquery_per_ads_manager = Subquery(
            ADS.objects.filter(ads_manager=OuterRef("ads_manager_id"))
            .annotate(
                latest_update_log=Subquery(latest_log_qs.values("update_at")[:1]),
                latest_update_log_is_complete=Subquery(
                    latest_log_qs.values("is_complete")[:1]
                ),
                latest_update_log_is_outdated=Case(
                    When(
                        latest_update_log__lt=ExpressionWrapper(
                            Now() - timedelta(days=ADSUpdateLog.OUTDATED_LOG_DAYS),
                            output_field=DateTimeField(),
                        ),
                        then=Value(True),
                    ),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
            )
            .filter(
                latest_update_log_is_complete=True, latest_update_log_is_outdated=False
            )
            .values("ads_manager")
            .annotate(count=Count("pk"))
            .values("count")[:1],
            output_field=IntegerField(),
        )

        context["user_ads_manager_requests"] = (
            ADSManagerRequest.objects.filter(user=self.request.user)
            .annotate(
                nb_ads=Coalesce(
                    ads_count_subquery, Value(0), output_field=IntegerField()
                ),
                complete_updates_count=Coalesce(
                    complete_updates_subquery_per_ads_manager,
                    Value(0),
                    output_field=IntegerField(),
                ),
                pourcentage_completion=Case(
                    When(
                        nb_ads__gt=0,
                        then=Round(
                            Cast(F("complete_updates_count"), FloatField())
                            * Value(100.0)
                            / Cast(F("nb_ads"), FloatField()),
                        ),
                    ),
                    default=Value(0),
                    output_field=IntegerField(),
                ),
                tri_bool=Case(
                    When(accepted=True, then=Value(0)),
                    When(accepted__isnull=True, then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField(),
                ),
            )
            .order_by("tri_bool")
        )

        return context


class ADSManagerView(ListView, ProcessFormView):
    template_name = "pages/ads_register/ads_manager.html"
    model = ADS
    paginate_by = 50

    def dispatch(self, request, *args, **kwargs):
        self.kwargs = kwargs
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return ListView.get(self, request, *args, **kwargs)

    def get_ads_manager(self):
        return ADSManager.objects.prefetch_related("adsmanagerdecree_set").get(
            id=self.kwargs["manager_id"]
        )

    def get_form(self):
        if self.request.method == "POST":
            return ADSManagerEditForm(
                instance=self.get_ads_manager(), data=self.request.POST
            )
        return ADSManagerEditForm(instance=self.get_ads_manager())

    def form_valid(self, form):
        form.save()
        return redirect("app.ads-manager.detail", manager_id=self.kwargs["manager_id"])

    def form_invalid(self, form):
        return self.get(self.request, *self.args, **self.kwargs)

    def annotate_with_update_logs(self, qs):
        # annotate the latest ADSUpdateLog.update_date
        latest_log_qs = ADSUpdateLog.objects.filter(ads=OuterRef("pk")).order_by(
            "-update_at"
        )
        qs = qs.annotate(
            latest_update_log=Subquery(latest_log_qs.values("update_at")[:1]),
            latest_update_log_is_complete=Subquery(
                latest_log_qs.values("is_complete")[:1]
            ),
            latest_update_log_is_outdated=Case(
                When(
                    latest_update_log__lt=ExpressionWrapper(
                        Now() - timedelta(days=ADSUpdateLog.OUTDATED_LOG_DAYS),
                        output_field=DateTimeField(),
                    ),
                    then=Value(True),
                ),
                default=Value(False),
                output_field=BooleanField(),
            ),
        )
        return qs

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(ads_manager__id=self.kwargs["manager_id"])

        if self.request.GET.get("accepted_cpam") == "on":
            qs = qs.filter(accepted_cpam=True)

        if self.request.GET.get("search"):
            search = self.request.GET.get("search")
            qs = qs.annotate(
                clean_immatriculation_plate=Replace(
                    "immatriculation_plate", Value("-"), Value("")
                )
            )

            qs = qs.filter(
                Q(owner_siret__icontains=search)
                | Q(adsuser__name__icontains=search)
                | Q(adsuser__siret__icontains=search)
                | Q(owner_name__icontains=search)
                | Q(clean_immatriculation_plate__icontains=search)
                | Q(epci_commune__libelle__icontains=search)
                | Q(number__icontains=search)
            )
        qs = self.annotate_with_update_logs(qs)

        # Add ordering on the number. CAST is necessary
        # in the case the ADS number is not an integer.
        # TODO: A remplacer, extra ne sera bientot plus supporté par django.
        qs_ordered = qs.extra(
            select={
                "ads_number_as_int": "CAST(substring(number FROM '^[0-9]+') AS NUMERIC)"
            }
        )

        # First, order by number if it is an integer, then by string.
        return qs_ordered.annotate(c=Count("id")).order_by(
            "ads_number_as_int", "number"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["edit_form"] = self.get_form()
        context["ads_manager"] = context["edit_form"].instance

        all_ads = self.annotate_with_update_logs(
            ADS.objects.filter(ads_manager__id=self.kwargs["manager_id"])
        )
        all_ads_counts = all_ads.aggregate(
            total=Count("id"),
            verified=Count(
                "id",
                filter=Q(
                    latest_update_log_is_complete=True,
                    latest_update_log_is_outdated=False,
                ),
            ),
        )

        context["dernier_arrete"] = (
            ADSManagerDecree.objects.filter(ads_manager__id=self.kwargs["manager_id"])
            .order_by("-date_arrete", "-id")
            .first()
        )

        context["ads_count"] = all_ads_counts["total"]
        context["pourcentage_verification"] = int(
            (all_ads_counts["verified"] / all_ads_counts["total"] * 100)
            if all_ads_counts["total"]
            else 0
        )

        return context


class ADSManagerArreteView(TemplateView):
    template_name = "pages/ads_register/ads_manager_arretes.html"

    def post(self, request, *args, **kwargs):
        manager_id = kwargs["manager_id"]
        ads_manager = get_object_or_404(ADSManager, id=manager_id)
        form = ADSManagerDecreeForm(data=request.POST, files=request.FILES)
        if form.is_valid():
            ADSManagerDecree.objects.create(
                ads_manager=ads_manager,
                file=form.cleaned_data["file"],
                date_arrete=form.cleaned_data["date_arrete"],
                nombre_ads=form.cleaned_data["nombre_ads"],
            )
            messages.success(request, "L'arrêté a bien été enregistré.")
            return super().get(request, *args, **kwargs)
        else:
            context = self.get_context_data(**kwargs)
            context["form"] = form
            messages.error(
                request, "Une erreur est survenue lors de l'enregistrement de l'arrêté."
            )
            return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        manager_id = kwargs["manager_id"]
        ads_manager = get_object_or_404(ADSManager, id=manager_id)
        arretes = ADSManagerDecree.objects.filter(ads_manager=ads_manager).order_by(
            "-date_arrete", "-id"
        )
        dernier_arrete = arretes.first()
        if dernier_arrete:
            context["arretes"] = arretes.exclude(id=dernier_arrete.id)
        context["dernier_arrete"] = dernier_arrete
        context["ads_manager"] = ads_manager
        context["form"] = ADSManagerDecreeForm()
        return context


class ADSManagerArreteUpdateView(View):
    def post(self, request, *args, **kwargs):
        arrete_id = self.kwargs.get("arrete_id")
        arrete = get_object_or_404(ADSManagerDecree, id=arrete_id)
        try:
            arrete.date_arrete = request.POST.get("date_arrete")
            arrete.nombre_ads = request.POST.get("nombre_ads")
            arrete.save()
            messages.success(request, "L'arrêté a bien été modifié.")
        except Exception:
            messages.error(
                request, "Une erreur est survenue lors de l'enregistrement de l'arrêté."
            )

        manager_id = kwargs["manager_id"]
        return redirect(
            reverse("app.ads-manager.decree.detail", kwargs={"manager_id": manager_id})
        )


class ADSManagerArreteDeleteView(View):
    def post(self, request, *args, **kwargs):
        arrete_id = self.kwargs.get("arrete_id")
        arrete = get_object_or_404(ADSManagerDecree, id=arrete_id)
        try:
            arrete.delete()
            messages.success(request, "L'arrêté a bien été supprimé.")
        except Exception:
            messages.error(
                request, "Une erreur est survenue lors de la suppression de l'arrêté."
            )

        manager_id = kwargs["manager_id"]
        return redirect(
            reverse("app.ads-manager.decree.detail", kwargs={"manager_id": manager_id})
        )


class ADSManagerAutocompleteView(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        query = ADSManager.objects.annotate(
            value=Unaccent(
                Case(
                    When(content_type__model="commune", then="commune__libelle"),
                    When(content_type__model="prefecture", then="prefecture__libelle"),
                    When(content_type__model="epci", then="epci__name"),
                    output_field=CharField(),
                )
            )
        ).annotate(
            location=Unaccent(
                Case(
                    When(content_type__model="commune", then="commune__insee"),
                    When(content_type__model="prefecture", then="prefecture__numero"),
                    When(content_type__model="epci", then="epci__departement"),
                    output_field=CharField(),
                )
            )
        )
        query = query.filter(
            Q(value__icontains=self.q) | Q(location__startswith=self.q)
        )
        return (
            query.filter(Q(value__icontains=self.q) | Q(location__startswith=self.q))
            # For communes, only display if the type is "COM".
            # For other types, display all.
            .filter(
                Q(
                    commune__type_commune="COM",
                )
                | Q(commune__isnull=True)
            )
            .order_by("value")
        )

    def get_result_label(self, ads_manager):
        """Display human_name instead of the default __str__."""
        return ads_manager.human_name()
