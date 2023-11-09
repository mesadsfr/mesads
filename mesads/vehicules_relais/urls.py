from django.contrib.auth.decorators import login_required
from django.urls import path

from . import views
from .decorators import proprietaire_required


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
        "proprietaire/<int:proprietaire_id>",
        proprietaire_required(views.ProprietaireDetailView.as_view()),
        name="vehicules-relais.proprietaire.detail",
    ),
    path(
        "proprietaire/<int:proprietaire_id>/nouveau_vehicule",
        proprietaire_required(views.ProprietaireVehiculeCreateView.as_view()),
        name="vehicules-relais.proprietaire.vehicule.new",
    ),
    path(
        "proprietaire/<int:proprietaire_id>/vehicules/<str:vehicule_numero>",
        proprietaire_required(views.ProprietaireVehiculeUpdateView.as_view()),
        name="vehicules-relais.proprietaire.vehicule.edit",
    ),
]
