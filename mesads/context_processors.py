from django.conf import settings

from mesads.app.models import (
    ADSManagerRequest,
    DemandeAccesLectureSeule,
    DemandeGestionPrefecture,
)


def mesads_settings(request):
    """Expose settings starting with MESADS_ to templates."""
    return {
        key: getattr(settings, key)
        for key in dir(settings)
        if key.startswith("MESADS_")
    }


def user_roles(request):
    context = {"user": request.user}

    if request.user.is_authenticated:
        gestionnaire_prefecture = request.user.demandes_gestion_prefecture.filter(
            statut=DemandeGestionPrefecture.ACCEPTE
        )
        ads_manager_requests = request.user.adsmanagerrequest_set.all()
        proprietaire_vehicule_relais = request.user.proprietaire_set.all()
        inspecteurs = request.user.demandes_acces_lecture_seule.filter(
            statut=DemandeAccesLectureSeule.ACCEPTE
        )
        if len(gestionnaire_prefecture):
            context["administrateur_ads"] = True
            context["ads_manager_administrator"] = (
                gestionnaire_prefecture.first().administrator
            )
        elif len(inspecteurs):
            context["inspecteur"] = True
        elif len(ads_manager_requests):
            context["manager_ads"] = True
            context["requetes_gestionnaires"] = ADSManagerRequest.objects.filter(
                user=request.user
            )
        elif len(proprietaire_vehicule_relais):
            context["proprietaire_vehicule_relais"] = True

    return context
