import json
import math

from django.db.models import OuterRef, Subquery, Count, IntegerField, BooleanField, Q
from django.db.models.functions import TruncMonth
from django.views.generic import TemplateView

from ..forms import ADSManagerAutocompleteForm
from ..models import (
    ADS,
    ADSManager,
    ADSManagerRequest,
    ADSUpdateLog,
    ADSManagerAdministrator,
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

    def get_statistiques(self):
        ads_administrators = ADSManagerAdministrator.objects.select_related(
            "prefecture"
        ).annotate(
            ads_count=Count(
                "adsmanager__ads",
                filter=Q(adsmanager__ads__deleted_at__isnull=True),
                distinct=True,
            )
        )
        stats = {
            "prefecture_taux_enregistrement": 0,
            "taux_enregistrement": 0,
            "total_ads": 0,
        }
        total_expected = 0

        for ads_administrator in ads_administrators:
            if ads_administrator.expected_ads_count:
                taux = (
                    ads_administrator.ads_count / ads_administrator.expected_ads_count
                )
                if taux >= 0.7:
                    stats["prefecture_taux_enregistrement"] += 1
                total_expected += ads_administrator.expected_ads_count
            stats["total_ads"] += ads_administrator.ads_count

        stats["taux_enregistrement"] = (
            math.floor((stats["total_ads"] / total_expected) * 100)
            if total_expected
            else 0
        )

        return stats

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["title"] = "Accueil - découvrez MesADS"
        context["stats"] = self.get_statistiques()

        if self.request.user.is_authenticated:
            ads_manager_administrators = (
                self.request.user.adsmanageradministrator_set.all()
            )
            ads_manager_requests = self.request.user.adsmanagerrequest_set.all()
            proprietaire_vehicule_relais = self.request.user.proprietaire_set.all()
            if len(ads_manager_administrators):
                context["administrateur_ads"] = True
                context["ads_manager_administrator"] = (
                    ads_manager_administrators.first()
                )

                context["title"] = (
                    f"MesADS - Accueil {context['ads_manager_administrator'].prefecture.display_text()}"
                )
            elif len(ads_manager_requests):
                context["manager_ads"] = True
                context["title"] = "MesADS - Accueil gestionnaire"
                # All ADS for the manager
                ads_count_subquery = (
                    ADS.objects.filter(
                        ads_manager=OuterRef("ads_manager_id"),
                        deleted_at__isnull=True,
                    )
                    .values("ads_manager")
                    .annotate(count=Count("*"))
                    .values("count")[:1]
                )

                # For each ADS, get its latest is_complete flag
                latest_complete = Subquery(
                    ADSUpdateLog.objects.filter(ads=OuterRef("pk"))
                    .order_by("-update_at")
                    .values("is_complete")[:1],
                    output_field=BooleanField(),
                )

                # 2) Count how many ADS under this manager have latest_complete=True
                complete_updates_subquery_per_ads_manager = Subquery(
                    ADS.objects.filter(ads_manager=OuterRef("ads_manager_id"))
                    .annotate(latest_complete=latest_complete)
                    .filter(latest_complete=True)
                    .values("ads_manager")
                    .annotate(count=Count("pk"))
                    .values("count")[:1],
                    output_field=IntegerField(),
                )

                context["requetes_gestionnaires"] = ADSManagerRequest.objects.filter(
                    user=self.request.user
                ).annotate(
                    ads_count=Subquery(ads_count_subquery, output_field=IntegerField()),
                    complete_updates_count=Subquery(
                        complete_updates_subquery_per_ads_manager,
                        output_field=IntegerField(),
                    ),
                )
            elif len(proprietaire_vehicule_relais):
                context["title"] = "MesADS - Accueil propriétaire de taxis relais"
                context["proprietaire_vehicule_relais"] = True

        return context


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
