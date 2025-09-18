from django.conf import settings
from mesads.app.models import ADSManagerRequest


def mesads_settings(request):
    """Expose settings starting with MESADS_ to templates."""
    return {
        key: getattr(settings, key)
        for key in dir(settings)
        if key.startswith("MESADS_")
    }


def user_roles(request):
    context = {}

    if request.user.is_authenticated:
        ads_manager_administrators = request.user.adsmanageradministrator_set.all()
        ads_manager_requests = request.user.adsmanagerrequest_set.all()
        proprietaire_vehicule_relais = request.user.proprietaire_set.all()
        if len(ads_manager_administrators):
            context["administrateur_ads"] = True
            context["ads_manager_administrator"] = ads_manager_administrators.first()
        elif len(ads_manager_requests):
            context["manager_ads"] = True
            context["requetes_gestionnaires"] = ADSManagerRequest.objects.filter(
                user=request.user
            )
        elif len(proprietaire_vehicule_relais):
            context["proprietaire_vehicule_relais"] = True

    return context
