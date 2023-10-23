from django.contrib.auth.decorators import login_required
from django.urls import path

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
        "consulter/departements/<str:departement>",
        views.SearchDepartementView.as_view(),
        name="vehicules-relais.search.departement",
    ),
    path(
        "consulter/vehicules/<str:numero>",
        views.VehiculeView.as_view(),
        name="vehicules-relais.vehicule",
    ),
    path(
        "proprietaire",
        login_required(views.ProprietaireListView.as_view()),
        name="vehicules-relais.proprietaire",
    ),
    path(
        "proprietaire/nouveau",
        login_required(views.ProprietaireCreateView.as_view()),
        name="vehicules-relais.proprietaire.new",
    ),
    path(
        "proprietaire/<int:id>",
        login_required(views.ProprietaireDetailView.as_view()),
        name="vehicules-relais.proprietaire.detail",
    ),
]
