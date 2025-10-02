from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.urls import path
from django.views.generic import TemplateView

from . import views
from .decorators import (
    ads_manager_required,
    ads_manager_administrator_required,
)

url_prefectures = [
    path(
        "espace-prefecture/<int:prefecture_id>/administrations/",
        ads_manager_administrator_required(views.ADSManagerAdministratorView.as_view()),
        name="app.ads-manager-admin.administrations",
    ),
    path(
        "espace-prefecture/<int:prefecture_id>/demandes-gestion/",
        ads_manager_administrator_required(views.ADSManagerAdminRequestsView.as_view()),
        name="app.ads-manager-admin.requests",
    ),
    path(
        "espace-prefecture/<int:prefecture_id>/administrations/<int:manager_id>/",
        ads_manager_administrator_required(views.ADSManagerView.as_view()),
        name="app.ads-manager-admin.detail-administration",
    ),
    path(
        "espace-prefecture/<int:prefecture_id>/administrations/<int:manager_id>/arretes",
        ads_manager_administrator_required(views.ads_manager_decree_view),
        name="app.ads-manager-admin.administration-arretes",
    ),
    path(
        "espace-prefecture/<int:prefecture_id>/administrations/<int:manager_id>/ads/",
        ads_manager_administrator_required(views.ADSCreateView.as_view()),
        name="app.ads-manager-admin.ads-create",
    ),
    path(
        "espace-prefecture/<int:prefecture_id>/administrations/<int:manager_id>/ads/<int:ads_id>",
        ads_manager_administrator_required(views.ADSView.as_view()),
        name="app.ads-manager-admin.ads-detail",
    ),
    path(
        "espace-prefecture/<int:prefecture_id>/administrations/<int:manager_id>/ads/<int:ads_id>/arrete",
        ads_manager_administrator_required(views.ADSDecreeView.as_view()),
        name="app.ads-manager-admin.ads-decree",
    ),
    path(
        "espace-prefecture/<int:prefecture_id>/administrations/<int:manager_id>/ads/<int:ads_id>/history",
        ads_manager_administrator_required(views.ADSHistoryView.as_view()),
        name="app.ads-manager-admin.ads-history",
    ),
    path(
        "espace-prefecture/<int:prefecture_id>/administrations/<int:manager_id>/ads/<int:ads_id>/delete",
        ads_manager_administrator_required(views.ADSDeleteView.as_view()),
        name="app.ads-manager-admin.ads-delete",
    ),
    path(
        "espace-prefecture/<int:prefecture_id>/changements",
        ads_manager_administrator_required(views.ADSManagerAdminUpdatesView.as_view()),
        name="app.ads-manager-admin.updates",
    ),
    path(
        "espace-prefecture/<int:prefecture_id>/demande_gestion_ads/",
        ads_manager_administrator_required(views.DemandeGestionADSView.as_view()),
        name="app.ads-manager-admin.demande_gestion_ads",
    ),
    path(
        "espace-prefecture/<int:prefecture_id>/vehicules-relais/",
        ads_manager_administrator_required(
            views.RepertoireVehiculeRelaisView.as_view()
        ),
        name="app.ads-manager-admin.vehicules_relais",
    ),
    path(
        "espace-prefecture/<int:prefecture_id>/vehicules-relais/<str:numero>/",
        ads_manager_administrator_required(views.VehiculeView.as_view()),
        name="app.ads-manager-admin.vehicule_relais_detail",
    ),
    path(
        "registre_ads/prefectures/<int:prefecture_id>/export",
        ads_manager_administrator_required(views.PrefectureExportView.as_view()),
        name="app.exports.prefecture",
    ),
]

url_gestionnaire = [
    path(
        "registre_ads/demande_gestion_ads/",
        login_required(views.DemandeGestionADSView.as_view()),
        name="app.ads-manager.demande_gestion_ads",
    ),
    path(
        "registre_ads/gestion/<int:manager_id>/",
        ads_manager_required(views.ADSManagerView.as_view()),
        name="app.ads-manager.detail",
    ),
    path(
        "registre_ads/gestion/<int:manager_id>/arrete",
        ads_manager_required(views.ads_manager_decree_view),
        name="app.ads-manager.decree.detail",
    ),
    path(
        "registre_ads/gestion/<int:manager_id>/export",
        ads_manager_required(views.ADSManagerExportView.as_view()),
        name="app.exports.ads-manager",
    ),
    path(
        "registre_ads/gestion/<int:manager_id>/ads/<int:ads_id>",
        ads_manager_required(views.ADSView.as_view()),
        name="app.ads.detail",
    ),
    path(
        "registre_ads/gestion/<int:manager_id>/ads/<int:ads_id>/delete",
        ads_manager_required(views.ADSDeleteView.as_view()),
        name="app.ads.delete",
    ),
    path(
        "registre_ads/gestion/<int:manager_id>/ads/",
        ads_manager_required(views.ADSCreateView.as_view()),
        name="app.ads.create",
    ),
    path(
        "registre_ads/gestion/<int:manager_id>/ads/<int:ads_id>/arrete",
        ads_manager_required(views.ADSDecreeView.as_view()),
        name="app.ads.decree",
    ),
    path(
        "registre_ads/gestion/<int:manager_id>/ads/<int:ads_id>/history",
        ads_manager_required(views.ADSHistoryView.as_view()),
        name="app.ads.history",
    ),
]

url_commons = [
    path(
        "registre_ads/dashboards",
        staff_member_required(views.DashboardsView.as_view()),
        name="app.dashboards.list",
    ),
    path(
        "gestionnaire_ads/autocomplete",
        views.ADSManagerAutocompleteView.as_view(),
        name="app.autocomplete.ads-manager",
    ),
]


url_public = [
    path("", views.HomepageView.as_view(), name="app.homepage"),
    path("faq", views.FAQView.as_view(), name="app.faq"),
    path(
        "mentions-legales",
        TemplateView.as_view(template_name="pages/mentions-legales.html"),
        name="app.legal",
    ),
    path(
        "suivi",
        TemplateView.as_view(template_name="pages/suivi.html"),
        name="app.suivi",
    ),
    path("chiffres-cles", views.StatsView.as_view(), name="app.stats"),
    path(
        "accessibilite",
        TemplateView.as_view(template_name="pages/accessibility.html"),
        name="app.accessibility",
    ),
    path(
        "cgu",
        TemplateView.as_view(template_name="pages/cgu.html"),
        name="app.cgu",
    ),
    path(
        "reglementation",
        views.ReglementationView.as_view(),
        name="app.reglementation",
    ),
]


urlpatterns = url_prefectures + url_gestionnaire + url_commons + url_public
