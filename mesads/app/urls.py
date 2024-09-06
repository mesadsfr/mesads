from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.urls import path
from django.views.generic import TemplateView

from . import views
from .decorators import (
    ads_manager_required,
    ads_manager_administrator_required,
)


urlpatterns = [
    path(
        "registre_ads/",
        login_required(views.ADSRegisterView.as_view()),
        name="app.ads-register.index",
    ),
    path(
        "registre_ads/dashboards",
        staff_member_required(views.DashboardsView.as_view()),
        name="app.dashboards.list",
    ),
    path(
        "registre_ads/dashboards/<int:ads_manager_administrator_id>/",
        staff_member_required(views.DashboardsDetailView.as_view()),
        name="app.dashboards.detail",
    ),
    path(
        "registre_ads/admin_gestion",
        ads_manager_administrator_required(views.ADSManagerAdminView.as_view()),
        name="app.ads-manager-admin.index",
    ),
    path(
        "registre_ads/gestion",
        login_required(views.ADSManagerRequestView.as_view()),
        name="app.ads-manager.index",
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
    path(
        "registre_ads/prefectures/<int:prefecture_id>/export",
        ads_manager_administrator_required(views.PrefectureExportView.as_view()),
        name="app.exports.prefecture",
    ),
    path(
        "gestionnaire_ads/autocomplete",
        views.ADSManagerAutocompleteView.as_view(),
        name="app.autocomplete.ads-manager",
    ),
]


urlpatterns += [
    path("", views.HomepageView.as_view(), name="app.homepage"),
    path("faq", views.FAQView.as_view(), name="app.faq"),
    path(
        "suivi",
        TemplateView.as_view(template_name="pages/suivi.html"),
        name="app.suivi",
    ),
    path(
        "gestionnaire_ads",
        TemplateView.as_view(template_name="pages/profiles_ads_manager.html"),
        name="app.profiles.ads_manager",
    ),
    path(
        "prefecture",
        TemplateView.as_view(
            template_name="pages/profiles_ads_manager_administrator.html"
        ),
        name="app.profiles.ads_manager_administrator",
    ),
    path(
        "chauffeur",
        TemplateView.as_view(template_name="pages/profiles_driver.html"),
        name="app.profiles.driver",
    ),
    path(
        "proprietaire_vehicules_relais",
        TemplateView.as_view(template_name="pages/profiles_vehicules_relais.html"),
        name="app.profiles.vehicules-relais",
    ),
    path("chiffres-cles", views.StatsView.as_view(), name="app.stats"),
    path(
        "accessibilite",
        TemplateView.as_view(template_name="pages/accessibility.html"),
        name="app.accessibility",
    ),
    path(
        "reglementation",
        views.ReglementationView.as_view(),
        name="app.reglementation",
    ),
]
