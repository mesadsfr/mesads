import functools

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

from .models import ADSManagerRequest, ADSManagerAdministrator


def ads_manager_required(func):
    """Returns 404 if there is no ADSManagerRequest for this user with the the
    flag "accepted" set to True, or if the user is not administrator.
    """
    @functools.wraps(func)
    def wrapped(request, manager_id=None, *args, **kwargs):
        if not ADSManagerAdministrator.objects.filter(
            ads_managers__in=[manager_id],
            users__in=[request.user]
        ).count():
            get_object_or_404(
                ADSManagerRequest,
                user=request.user,
                ads_manager__id=manager_id,
                accepted=True,
            )
        return func(request, manager_id=manager_id, *args, **kwargs)
    return login_required(wrapped)
