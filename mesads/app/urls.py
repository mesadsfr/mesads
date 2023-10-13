from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.urls import path
from django.views.generic import RedirectView, TemplateView

from . import views
from .decorators import (
    ads_manager_required,
    ads_manager_administrator_required,
)


urlpatterns = [
    path("", login_required(views.HomepageView.as_view()), name="app.homepage"),
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
    # When the user makes a request to become an ADSManager, we send an email to
    # the administrator. This email used to contain a link to /admin_gestion.
    # For backward compatibility, we redirect the user to the new URL
    # /registre_ads/admin_gestion.
    path(
        "admin_gestion",
        RedirectView.as_view(url="/registre_ads/admin_gestion", permanent=True),
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
        ads_manager_administrator_required(views.prefecture_export_ads),
        name="app.exports.prefecture",
    ),
]


urlpatterns += [
    path("faq", views.FAQView.as_view(), name="app.faq"),
    path(
        "profils",
        TemplateView.as_view(template_name="pages/profils.html"),
        name="app.profils",
    ),
    path(
        "profils/aom",
        TemplateView.as_view(template_name="pages/profils_aom.html"),
        name="app.profils.aom",
    ),
    path(
        "profils/chauffeur",
        TemplateView.as_view(template_name="pages/profils_driver.html"),
        name="app.profils.driver",
    ),
    path(
        "profils/autre",
        TemplateView.as_view(template_name="pages/profils_other.html"),
        name="app.profils.other",
    ),
    path("chiffres-cles", views.StatsView.as_view(), name="app.stats"),
]
