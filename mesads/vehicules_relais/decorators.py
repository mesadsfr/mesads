import functools

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404

from .models import Proprietaire, Vehicule


def proprietaire_required(func):
    """
    Returns 404 if the user is not administrator
    and not proprietaire of the ressource.
    """

    @functools.wraps(func)
    def wrapped(request, proprietaire_id=None, *args, **kwargs):
        if request.user.is_staff:
            proprietaire = get_object_or_404(Proprietaire, id=proprietaire_id)
        else:
            proprietaire = get_object_or_404(
                Proprietaire, id=proprietaire_id, users__in=[request.user]
            )
        return func(
            request,
            proprietaire_id=proprietaire_id,
            proprietaire=proprietaire,
            *args,
            **kwargs,
        )

    return login_required(wrapped)


def proprietaire_or_prefecture_required(func):
    """
    Returns 404 if the user is not administrator, adsmanageradministrator
    and not proprietaire of the ressource.
    """

    @functools.wraps(func)
    def wrapped(request, proprietaire_id=None, vehicule_numero=None, *args, **kwargs):
        demande_prefecture = request.user.demandes_gestion_prefecture.first()
        if request.user.is_staff:
            proprietaire = get_object_or_404(Proprietaire, id=proprietaire_id)
        elif demande_prefecture:
            vehicule = get_object_or_404(Vehicule, numero=vehicule_numero)
            if vehicule.departement == demande_prefecture.administrator.prefecture:
                proprietaire = vehicule.proprietaire
            else:
                raise Http404()
        else:
            proprietaire = get_object_or_404(
                Proprietaire, id=proprietaire_id, users__in=[request.user]
            )
        return func(
            request,
            proprietaire_id=proprietaire_id,
            vehicule_numero=vehicule_numero,
            proprietaire=proprietaire,
            *args,
            **kwargs,
        )

    return login_required(wrapped)
