from django.contrib.auth.decorators import login_required
from django.urls import path

from . import views
from .decorators import ads_manager_required


urlpatterns = [
    path('', views.HomepageView.as_view(), name='homepage'),
    path('comment-ca-marche', views.HowItWorksView.as_view(), name='how-it-works'),
    path('admin_gestionnaires', login_required(views.ADSManagerAdminView.as_view()), name='ads-manager-admin'),
    path('demande_gestion', login_required(views.ADSManagerRequestView.as_view()), name='ads-manager-request'),
    path('ads_gestion/<int:manager_id>/', ads_manager_required(views.ADSManagerView.as_view()), name='ads-manager'),
    path('ads/<int:ads_id>', ads_manager_required(views.ADSView.as_view()), name='ads'),
]
