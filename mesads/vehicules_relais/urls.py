from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.urls import path
from django.views.generic import RedirectView, TemplateView

from . import views


urlpatterns = [
    path(
        "",
        views.IndexView.as_view(),
        name="vehicules-relais.index",
    ),
    path(
        "consulter",
        views.SearchView.as_view(),
        name="vehicules-relais.search",
    ),
    path(
        "consulter/<str:departement>",
        views.SearchDepartementView.as_view(),
        name="vehicules-relais.search.departement",
    ),
    path(
        "enregistrer",
        views.RegisterView.as_view(),
        name="vehicules-relais.register",
    ),
]
