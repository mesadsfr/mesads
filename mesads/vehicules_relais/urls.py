from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
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
        "proprietaire/<int:proprietaire_id>/supprimer",
        proprietaire_required(views.ProprietaireDeleteView.as_view()),
        name="vehicules-relais.proprietaire.delete",
    ),
    path(
        "proprietaire/<int:proprietaire_id>/modifier",
        proprietaire_required(views.ProprietaireEditView.as_view()),
        name="vehicules-relais.proprietaire.edit",
    ),
    path(
        "proprietaire/<int:proprietaire_id>/historique",
        staff_member_required(
            proprietaire_required(views.ProprietaireHistoryView.as_view())
        ),
        name="vehicules-relais.proprietaire.history",
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
    path(
        "proprietaire/<int:proprietaire_id>/vehicules/<str:vehicule_numero>/supprimer",
        proprietaire_required(views.ProprietaireVehiculeDeleteView.as_view()),
        name="vehicules-relais.proprietaire.vehicule.delete",
    ),
    path(
        "proprietaire/<int:proprietaire_id>/vehicules/<str:vehicule_numero>/historique",
        staff_member_required(
            proprietaire_required(views.ProprietaireVehiculeHistoryView.as_view())
        ),
        name="vehicules-relais.proprietaire.vehicule.history",
    ),
    path(
        "proprietaire/<int:proprietaire_id>/vehicules/<str:vehicule_numero>/recepisse",
        staff_member_required(
            proprietaire_required(views.ProprietaireVehiculeRecepisseView.as_view())
        ),
        name="vehicules-relais.proprietaire.vehicule.recepisse",
    ),
]
