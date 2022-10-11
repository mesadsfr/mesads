from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.urls import path

from . import views
from .decorators import (
    ads_manager_required,
    ads_manager_administrator_required,
)


urlpatterns = [
    path('', login_required(views.HomepageView.as_view()), name='app.homepage'),
    path('dashboards', staff_member_required(views.DashboardsView.as_view()), name='app.dashboards.list'),
    path('dashboards/<int:ads_manager_administrator_id>/', staff_member_required(views.DashboardsDetailView.as_view()), name='app.dashboards.detail'),
    path('admin_gestion', ads_manager_administrator_required(views.ADSManagerAdminView.as_view()), name='app.ads-manager-admin.index'),
    path('gestion', login_required(views.ADSManagerRequestView.as_view()), name='app.ads-manager.index'),
    path('gestion/<int:manager_id>/', ads_manager_required(views.ADSManagerView.as_view()), name='app.ads-manager.detail'),
    path('gestion/<int:manager_id>/ads/<int:ads_id>', ads_manager_required(views.ADSView.as_view()), name='app.ads.detail'),
    path('gestion/<int:manager_id>/ads/<int:ads_id>/delete', ads_manager_required(views.ADSDeleteView.as_view()), name='app.ads.delete'),
    path('gestion/<int:manager_id>/ads/', ads_manager_required(views.ADSCreateView.as_view()), name='app.ads.create'),
    path('prefectures/<int:prefecture_id>/export', ads_manager_administrator_required(views.prefecture_export_ads), name='app.exports.prefecture'),
]
