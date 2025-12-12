import math

from django.db.models import OuterRef, Subquery, Count, IntegerField, BooleanField, Q
from django.db.models.functions import ExtractQuarter, ExtractYear
from django.views.generic import TemplateView
from django.urls import reverse

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

            context["show_notation"] = self.request.user.show_notation()

        return context


class FAQView(TemplateView):
    template_name = "pages/faq.html"


class StatsView(TemplateView):
    template_name = "pages/stats.html"

    def build_trimester_dict(self, queryset):
        count_by_trimester = {}
        total_count = 0

        for trimester in queryset:
            year = trimester["year"]
            quarter = trimester["quarter"]

            suffix = "er" if quarter == 1 else "e"
            key = f"{quarter}{suffix} trimestre {year}"
            total_count += trimester["count"]
            count_by_trimester[key] = total_count

        return count_by_trimester

    def get_ads_by_trimester(self) -> dict[str, int]:
        """
        Fonction permettant de retrouver le nombre d'ADS créées pour chaque trimestre.
        Renvoie un dictionnaire de la forme { <trimestre>: <count> }
        Ou trimestre est une string décrivant le trimestre
        Par exemple: "2e Trimestre 2022"
        """
        qs_ads_by_trimester = (
            ADS.objects.annotate(
                year=ExtractYear("creation_date"),
                quarter=ExtractQuarter("creation_date"),
            )
            .values("year", "quarter")
            .annotate(count=Count("id"))
            .order_by("year", "quarter")
        )
        return self.build_trimester_dict(qs_ads_by_trimester)

    def get_ads_manager_by_trimester(self) -> dict[str, int]:
        """
        Fonction permettant de retrouver le nombre de comptes gestionnaire créés pour chaque trimestre.
        Renvoie un dictionnaire de la forme { <trimestre>: <count> }
        Ou trimestre est une string décrivant le trimestre
        Par exemple: "2e Trimestre 2022"
        """

        qs_ads_manager_by_trimester = (
            ADSManagerRequest.objects.filter(accepted=True)
            .annotate(
                year=ExtractYear("created_at"), quarter=ExtractQuarter("created_at")
            )
            .values("year", "quarter")
            .annotate(count=Count("id"))
            .order_by("year", "quarter")
        )
        return self.build_trimester_dict(qs_ads_manager_by_trimester)

    def get_proprietaire_by_trimester(self) -> dict[str, int]:
        qs_proprietaires_by_trimester = (
            Proprietaire.objects.filter(vehicule__isnull=False)
            .annotate(
                year=ExtractYear("created_at"), quarter=ExtractQuarter("created_at")
            )
            .values("year", "quarter")
            .annotate(count=Count("id", distinct=True))
            .order_by("year", "quarter")
        )
        return self.build_trimester_dict(qs_proprietaires_by_trimester)

    def get_vehicule_by_trimester(self) -> dict[str, int]:
        qs_vehicule_by_trimester = (
            Vehicule.objects.annotate(
                year=ExtractYear("created_at"), quarter=ExtractQuarter("created_at")
            )
            .values("year", "quarter")
            .annotate(count=Count("id", distinct=True))
            .order_by("year", "quarter")
        )
        return self.build_trimester_dict(qs_vehicule_by_trimester)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        stats_by_pref = get_stats_by_prefecture()
        context["stats_by_prefecture"] = [
            (prefecture, stats_by_pref.get(prefecture.numero))
            for prefecture in Prefecture.objects.order_by("numero").exclude(
                libelle__icontains="test"
            )
        ]

        context["ads_count"] = ADS.objects.count()

        context["ads_manager_requests_count"] = ADSManagerRequest.objects.filter(
            accepted=True
        ).count()

        context["ads_managers_count"] = (
            ADSManager.objects.annotate(ads_count=Count("ads"))
            .filter(ads_count__gt=0)
            .count()
        )

        context["relais_proprietaires_count"] = (
            Proprietaire.objects.annotate(vehicules_count=Count("vehicule"))
            .filter(vehicules_count__gt=0)
            .count()
        )
        context["relais_vehicules_count"] = Vehicule.objects.count()

        context["trimesters_data"] = {
            "ads_by_trimester": self.get_ads_by_trimester(),
            "ads_manager_by_trimester": self.get_ads_manager_by_trimester(),
            "proprietaire_by_trimester": self.get_proprietaire_by_trimester(),
            "vehicule_by_trimester": self.get_vehicule_by_trimester(),
        }
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


class PlanSiteView(TemplateView):
    template_name = "pages/plan_site.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        liens_base_1 = [
            {
                "nom_url": "Répertoire des taxis Relais",
                "url": reverse("vehicules-relais.index"),
            },
            {
                "nom_url": "Réglementation taxi",
                "url": reverse("app.reglementation"),
            },
            {"nom_url": "Foire aux questions", "url": reverse("app.faq")},
        ]
        liens_base_2 = [
            {
                "nom_url": "Conditions générales d'utilisation",
                "url": reverse("app.cgu"),
            },
            {"nom_url": "Mentions légales", "url": reverse("app.legal")},
            {
                "nom_url": "Données personnelles et cookies",
                "url": reverse("app.suivi"),
            },
            {
                "nom_url": "Déclaration d'accessibilité",
                "url": reverse("app.accessibility"),
            },
            {
                "nom_url": "Statistiques",
                "url": reverse("app.stats"),
            },
        ]

        if self.request.user.is_authenticated:
            liens_authentifie = [
                {
                    "nom_url": "Changer de mot de passe",
                    "url": reverse("password_change"),
                },
                {"nom_url": "Déconnexion", "url": reverse("oidc_logout")},
            ]
            ads_manager_administrators = (
                self.request.user.adsmanageradministrator_set.all()
            )
            liens_plan = []
            ads_manager_requests = self.request.user.adsmanagerrequest_set.all()
            proprietaire_vehicule_relais = self.request.user.proprietaire_set.all()
            if len(ads_manager_administrators):
                administrator = ads_manager_administrators.first()

                liens_plan = [
                    {
                        "nom_url": "Accès prefecture",
                        "url": reverse("app.homepage"),
                        "sub_urls": [
                            {
                                "nom_url": "Demande d'accès des gestionnaires rattachés à votre Préfecture",
                                "url": reverse(
                                    "app.ads-manager-admin.requests",
                                    kwargs={
                                        "prefecture_id": administrator.prefecture.id
                                    },
                                ),
                            },
                            {
                                "nom_url": "Données liées aux ADS de votre Préfecture",
                                "url": reverse(
                                    "app.ads-manager-admin.administrations",
                                    kwargs={
                                        "prefecture_id": administrator.prefecture.id
                                    },
                                ),
                            },
                            {
                                "nom_url": "Données liées aux répertoires des taxis relais de votre préfecture",
                                "url": reverse(
                                    "app.ads-manager-admin.vehicules_relais",
                                    kwargs={
                                        "prefecture_id": administrator.prefecture.id
                                    },
                                ),
                            },
                            {
                                "nom_url": "Modifications effectuées par les gestionnaires rattachés à votre Préfecture",
                                "url": reverse(
                                    "app.ads-manager-admin.updates",
                                    kwargs={
                                        "prefecture_id": administrator.prefecture.id
                                    },
                                ),
                            },
                        ],
                    }
                ]

            elif len(ads_manager_requests):
                liens_plan = [
                    {
                        "nom_url": "Demande de gestion d'une administration",
                        "url": reverse("app.ads-manager.demande_gestion_ads"),
                    },
                    {
                        "nom_url": "Administrations en gestions",
                        "url": reverse("app.homepage"),
                    },
                ]
            elif len(proprietaire_vehicule_relais):
                liens_plan = [
                    {
                        "nom_url": "Espace propriétaire",
                        "url": reverse("vehicules-relais.proprietaire"),
                    }
                ]
            else:
                liens_plan = [
                    {
                        "nom_url": "Demande de gestion d'une administration",
                        "url": reverse("app.ads-manager.demande_gestion_ads"),
                    },
                    {
                        "nom_url": "Créer un espace propriétaire de taxis relais",
                        "url": reverse("vehicules-relais.proprietaire.new"),
                    },
                ]
            context["liens_plan"] = (
                liens_base_1 + liens_authentifie + liens_plan + liens_base_2
            )
            return context
        else:
            liens_plan = [{"nom_url": "Se connecter", "url": reverse("login")}]
            context["liens_plan"] = liens_base_1 + liens_plan + liens_base_2
        return context
