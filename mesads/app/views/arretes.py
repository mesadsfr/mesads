from django.conf import settings
from django.http import Http404, FileResponse
from django.views import View
from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404

from mesads.app.models import ADSManager, ADS

from pathlib import Path


class ListeArretesFilesView(TemplateView):
    template_name = "pages/ads_register/arretes_liste.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.kwargs.get("manager_id"):
            context["ads_manager"] = get_object_or_404(
                ADSManager, id=self.kwargs.get("manager_id")
            )
        if self.request.GET.get("ads_id"):
            context["ads"] = get_object_or_404(ADS, id=self.request.GET.get("ads_id"))

        return context


class TelechargementArreteView(View):
    http_method_names = ["get"]

    CHANGEMENT_VEHICULE_OLD = "changement_vehicule_old"
    CHANGEMENT_VEHICULE_NEW = "changement_vehicule_new"
    NOMBRE_ADS = "nombre_ads"
    LOCATION_GERANCE = "location_gerance"
    CREATION_NOUVELLE_ADS = "creation_nouvelle_ads"
    RENOUVELLEMENT_ADS = "renouvellement_ads"
    CHANGEMENT_TITULAIRE = "changement_titulaire_old"

    modele_arretes = {
        CHANGEMENT_VEHICULE_OLD: {
            "file_path": "arrete_changement_vehicule_old.docx",
            "file_name": "Modèle arrêté changement de véhicule (ancienne ADS).docx",
        },
        CHANGEMENT_VEHICULE_NEW: {
            "file_path": "arrete_changement_vehicule_new.docx",
            "file_name": "Modèle arrêté changement de véhicule (nouvelle ADS).docx",
        },
        NOMBRE_ADS: {
            "file_path": "arrete_nombre_ads.docx",
            "file_name": "Modèle arrêté délimitant le nombre d'ADS autorisées sur le territoire d'une collectivité.docx",
        },
        LOCATION_GERANCE: {
            "file_path": "arrete_location_gerance.docx",
            "file_name": "Modèle arrêté passage en location gérance (ancienne ADS).docx",
        },
        CREATION_NOUVELLE_ADS: {
            "file_path": "arrete_creation_ads.docx",
            "file_name": "Modèle arrêté création nouvelle ADS.docx",
        },
        RENOUVELLEMENT_ADS: {
            "file_path": "arrete_renouvellement.docx",
            "file_name": "Modèle arrêté renouvellement 5 ans (nouvelle ADS).docx",
        },
        CHANGEMENT_TITULAIRE: {
            "file_path": "arrete_changement_titulaire.docx",
            "file_name": "Modèle arrêté changement de titulaire (ancienne ADS).docx",
        },
    }

    def get_full_file_path(self, file_path):
        return Path(settings.BASE_DIR) / "mesads" / "app" / "docs" / file_path

    def get(self, request, *args, **kwargs):
        if (
            not self.request.GET.get("modele_arrete")
            or self.request.GET.get("modele_arrete") not in self.modele_arretes.keys()
        ):
            raise Http404
        modele_arrete = self.request.GET.get("modele_arrete")

        file_path = self.get_full_file_path(
            self.modele_arretes[modele_arrete]["file_path"]
        )
        file_name = self.modele_arretes[modele_arrete]["file_name"]

        if not file_path.exists():
            raise Http404("Fichier introuvable")

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename=file_name,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
