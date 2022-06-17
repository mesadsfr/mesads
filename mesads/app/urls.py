from django.contrib.auth.decorators import login_required
from django.urls import path

from . import views
from .decorators import (
    ads_manager_required,
    ads_manager_administrator_required,
)


urlpatterns = [
    path('', views.HomepageView.as_view(), name='homepage'),
    path('admin_gestion', ads_manager_administrator_required(views.ADSManagerAdminView.as_view()), name='ads-manager-admin'),
    path('gestion', login_required(views.ADSManagerRequestView.as_view()), name='ads-manager-request'),
    path('gestion/<int:manager_id>/', ads_manager_required(views.ADSManagerView.as_view()), name='ads-manager'),
    path('gestion/<int:manager_id>/ads/<int:ads_id>', ads_manager_required(views.ADSView.as_view()), name='ads'),
    path('gestion/<int:manager_id>/ads/<int:ads_id>/delete', ads_manager_required(views.ADSDeleteView.as_view()), name='ads.delete'),
    path('gestion/<int:manager_id>/ads/', ads_manager_required(views.ADSCreateView.as_view()), name='ads.create'),
    path('prefectures/<int:prefecture_id>/export', ads_manager_administrator_required(views.prefecture_export_ads), name='prefecture_export_ads'),
]
