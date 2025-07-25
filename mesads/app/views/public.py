import json

from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.views.generic import TemplateView

from ..forms import ADSManagerAutocompleteForm
from ..models import (
    ADS,
    ADSManager,
    ADSManagerRequest,
)
from mesads.api.views import get_stats_by_prefecture
from mesads.fradm.models import Prefecture
from mesads.vehicules_relais.models import Proprietaire, Vehicule


class HTTP500View(TemplateView):
    """The default HTTP/500 handler can't access to context processors and does
    not have access to the variable MESADS_CONTACT_EMAIL.
    """

    template_name = "500.html"

    def dispatch(self, request, *args, **kwargs):
        """The base class TemplateView only accepts GET requests. By overriding
        dispatch, we return the error page for any other method."""
        return super().get(request, *args, **kwargs)


class HomepageView(TemplateView):
    template_name = "pages/homepage.html"


class FAQView(TemplateView):
    template_name = "pages/faq.html"


class StatsView(TemplateView):
    template_name = "pages/stats.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        stats_by_pref = get_stats_by_prefecture()
        context["stats_by_prefecture"] = [
            (prefecture, stats_by_pref.get(prefecture.numero))
            for prefecture in Prefecture.objects.order_by("numero").exclude(
                libelle__icontains="test"
            )
        ]

        if len(self.request.GET.getlist("q")) == 0:
            ads_managers_select_form = ADSManagerAutocompleteForm()
        else:
            ads_managers_select_form = ADSManagerAutocompleteForm(self.request.GET)

        context["ads_managers_select_form"] = ads_managers_select_form

        ads_managers_filter = []
        if ads_managers_select_form.is_valid():
            ads_managers_filter = ads_managers_select_form.cleaned_data["q"].all()

        context["ads_count"] = ADS.objects.count()
        context["ads_count_filtered"] = ADS.objects.filter(
            ads_manager__in=ads_managers_filter
        ).count()

        ads_count_by_month = (
            ADS.objects.annotate(month=TruncMonth("creation_date"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )
        context["ads_count_by_month"] = json.dumps(
            dict(
                ((row["month"].isoformat(), row["count"]) for row in ads_count_by_month)
            )
        )

        ads_count_by_month_filtered = (
            ADS.objects.filter(ads_manager__in=ads_managers_filter)
            .annotate(month=TruncMonth("creation_date"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )
        context["ads_count_by_month_filtered"] = json.dumps(
            dict(
                (
                    (row["month"].isoformat(), row["count"])
                    for row in ads_count_by_month_filtered
                )
            )
        )

        context["ads_manager_requests_count"] = ADSManagerRequest.objects.filter(
            accepted=True
        ).count()
        context["ads_manager_requests_count_filtered"] = (
            ADSManagerRequest.objects.filter(
                accepted=True, ads_manager__in=ads_managers_filter
            ).count()
        )

        ads_manager_requests_by_month = (
            ADSManagerRequest.objects.filter(accepted=True)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )
        context["ads_manager_requests_by_month"] = json.dumps(
            dict(
                (
                    (row["month"].isoformat(), row["count"])
                    for row in ads_manager_requests_by_month
                )
            )
        )

        ads_manager_requests_by_month_filtered = (
            ADSManagerRequest.objects.filter(ads_manager__in=ads_managers_filter)
            .filter(accepted=True)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )
        context["ads_manager_requests_by_month_filtered"] = json.dumps(
            dict(
                (
                    (row["month"].isoformat(), row["count"])
                    for row in ads_manager_requests_by_month_filtered
                )
            )
        )

        context["ads_managers_count"] = (
            ADSManager.objects.annotate(ads_count=Count("ads"))
            .filter(ads_count__gt=0)
            .count()
        )
        context["ads_managers_count_filtered"] = (
            ADSManager.objects.filter(id__in=ads_managers_filter)
            .annotate(ads_count=Count("ads"))
            .filter(ads_count__gt=0)
            .count()
        )

        context["relais_proprietaires_count"] = (
            Proprietaire.objects.annotate(vehicules_count=Count("vehicule"))
            .filter(vehicules_count__gt=0)
            .count()
        )
        context["relais_vehicules_count"] = Vehicule.objects.count()

        relais_proprietaires_by_month = (
            Proprietaire.objects.filter(vehicule__isnull=False)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id", distinct=True))
            .order_by("month")
        )
        context["relais_proprietaires_by_month"] = json.dumps(
            dict(
                (
                    (row["month"].isoformat(), row["count"])
                    for row in relais_proprietaires_by_month
                )
            )
        )

        relais_vehicules_by_month = (
            Vehicule.objects.annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )
        context["relais_vehicules_by_month"] = json.dumps(
            dict(
                (
                    (row["month"].isoformat(), row["count"])
                    for row in relais_vehicules_by_month
                )
            )
        )
        return context


class ReglementationView(TemplateView):
    template_name = "pages/reglementation.html"
    entries = [
        {
            "title": "Principes généraux",
            "articles": [
                {
                    "title": "Le rôle des collectivités",
                    "template": "pages/reglementation/principes_generaux/role_collectivites.html",
                },
                {
                    "title": "Qu'est-ce qu'une ADS ?",
                    "template": "pages/reglementation/principes_generaux/qu_est_ce_qu_une_ads.html",
                },
                {
                    "title": "Qui délivre les ADS ?",
                    "template": "pages/reglementation/principes_generaux/qui_delivre_ads.html",
                },
            ],
        },
        {
            "title": "Délivrance d'une ADS",
            "articles": [
                {
                    "menu_title": "Arrêté délimitant le nombre d'ADS",
                    "title": "Étape 1 : l'arrêté délimitant le nombre d'ADS",
                    "template": "pages/reglementation/delivrance_ads/arrete_delimitant_ads.html",
                },
                {
                    "menu_title": "Attribution de l'ADS",
                    "title": "Étape 2 : l'attribution de l'ADS",
                    "template": "pages/reglementation/delivrance_ads/attribution_ads.html",
                },
                {
                    "menu_title": "L'arrêté municipal",
                    "title": "Étape 3 : la notification de l'arrêté",
                    "template": "pages/reglementation/delivrance_ads/notification_arrete.html",
                },
                {
                    "menu_title": "Retrait d'une ADS",
                    "title": "Étape 4 : le retrait d'une ADS",
                    "template": "pages/reglementation/delivrance_ads/retrait_ads.html",
                },
            ],
        },
        {
            "title": "Répertoire des taxis relais",
            "articles": [
                {
                    "title": "Qu'est-ce qu'un taxi relais ?",
                    "template": "pages/reglementation/relais/definition.html",
                },
            ],
        },
    ]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["entries"] = self.entries
        return ctx
