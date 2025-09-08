from datetime import timedelta

from django.contrib import messages
from django.contrib.postgres.lookups import Unaccent
from django.db.models import (
    Count,
    Q,
    Value,
    Case,
    CharField,
    Subquery,
    OuterRef,
    ExpressionWrapper,
    DateTimeField,
    When,
    BooleanField,
)
from django.db.models.functions import Replace, Now
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic.edit import ProcessFormView
from django.views.generic.list import ListView


from dal import autocomplete

from ..forms import (
    ADSManagerDecreeFormSet,
    ADSManagerEditForm,
    ADSSearchForm,
)
from ..models import ADS, ADSManager, ADSUpdateLog


class ADSManagerView(ListView, ProcessFormView):
    template_name = "pages/ads_register/ads_manager.html"
    model = ADS
    paginate_by = 50

    def get(self, request, *args, **kwargs):
        self.search_form = ADSSearchForm(request.GET)
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

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(ads_manager__id=self.kwargs["manager_id"])

        if self.search_form.is_valid():
            if self.search_form.cleaned_data["accepted_cpam"] is not None:
                qs = qs.filter(
                    accepted_cpam=self.search_form.cleaned_data["accepted_cpam"]
                )

            q = self.search_form.cleaned_data["q"]
            if q:
                qs = qs.annotate(
                    clean_immatriculation_plate=Replace(
                        "immatriculation_plate", Value("-"), Value("")
                    )
                )

                qs = qs.filter(
                    Q(owner_siret__icontains=q)
                    | Q(adsuser__name__icontains=q)
                    | Q(adsuser__siret__icontains=q)
                    | Q(owner_name__icontains=q)
                    | Q(clean_immatriculation_plate__icontains=q)
                    | Q(epci_commune__libelle__icontains=q)
                    | Q(number__icontains=q)
                )

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

        # Add ordering on the number. CAST is necessary in the case the ADS number is not an integer.
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
        ctx = super().get_context_data(**kwargs)
        ctx["search_form"] = self.search_form

        # search_defined is a boolean, set to True of any of the search form
        # parameter is defined.
        ctx["search_defined"] = any(
            (v is not None and v != "" for v in self.search_form.cleaned_data.values())
        )

        ctx["edit_form"] = self.get_form()
        ctx["ads_manager"] = ctx["edit_form"].instance
        return ctx


def ads_manager_decree_view(request, manager_id):
    """Decree limiting the number of ADS for an ADSManager."""
    ads_manager = get_object_or_404(ADSManager, id=manager_id)

    if request.method == "POST":
        formset = ADSManagerDecreeFormSet(
            request.POST, request.FILES, instance=ads_manager
        )
        if formset.is_valid():
            formset.save()
            messages.success(request, "Les modifications ont été enregistrées.")
            return redirect("app.ads-manager.decree.detail", manager_id=manager_id)
    else:
        formset = ADSManagerDecreeFormSet(instance=ads_manager)

    return render(
        request,
        "pages/ads_register/ads_manager_decree.html",
        context={
            "ads_manager": ads_manager,
            "formset": formset,
        },
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
            # For communes, only display if the type is "COM". For other types, display all.
            .filter(
                Q(
                    commune__type_commune="COM",
                )
                | Q(commune__isnull=True)
            ).order_by("value")
        )

    def get_result_label(self, ads_manager):
        """Display human_name instead of the default __str__."""
        return ads_manager.human_name()
