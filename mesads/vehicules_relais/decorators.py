import functools

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

from .models import Proprietaire


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
