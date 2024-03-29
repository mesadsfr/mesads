import functools

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_list_or_404, get_object_or_404, redirect
from django.urls import resolve, reverse

from .models import ADS, ADSManagerRequest, ADSManagerAdministrator


def ads_manager_required(func):
    """Returns 404 if there is no ADSManagerRequest for this user with the the
    flag "accepted" set to True, or if the user is not administrator.
    """

    @functools.wraps(func)
    def wrapped(request, manager_id=None, *args, **kwargs):
        if (
            not request.user.is_staff
            and not ADSManagerAdministrator.objects.filter(
                adsmanager=manager_id, users__in=[request.user]
            ).count()
        ):
            get_object_or_404(
                ADSManagerRequest,
                user=request.user,
                ads_manager__id=manager_id,
                accepted=True,
            )
        if kwargs.get("ads_id"):
            # Make sure the ADS exists if the view is for an ADS
            ads = get_object_or_404(ADS, id=kwargs.get("ads_id"))

            # If the URL is with the form /xxx/<ads_manager_id>/xxx/<ads_id> but
            # <ads_manager_id> has been manually changed by the user and doesn't
            # match the actual manager_id, we redirect to the correct URL.
            if ads.ads_manager.id != manager_id:
                urlpattern = resolve(request.path_info)
                url = reverse(
                    urlpattern.url_name,
                    kwargs={"manager_id": ads.ads_manager.id, "ads_id": ads.id},
                )
                return redirect(url, permanent=True)
        return func(request, manager_id=manager_id, *args, **kwargs)

    return login_required(wrapped)


def ads_manager_administrator_required(func):
    @functools.wraps(func)
    def wrapped(request, prefecture_id=None, *args, **kwargs):
        # Staff user can access everything
        if request.user.is_staff and prefecture_id:
            ads_manager_administrator = get_object_or_404(
                ADSManagerAdministrator, prefecture=prefecture_id
            )
            return func(
                request,
                ads_manager_administrator=ads_manager_administrator,
                *args,
                **kwargs
            )

        # Make sure user has access to the ADSManagerAdministrator
        elif not request.user.is_staff and prefecture_id:
            ads_manager_administrator = get_object_or_404(
                ADSManagerAdministrator,
                prefecture=prefecture_id,
                users__in=[request.user],
            )
            return func(
                request,
                ads_manager_administrator=ads_manager_administrator,
                *args,
                **kwargs
            )

        # If prefecture_id is not provided, user must have access to at least one instance of ADSManagerAdministrator
        elif not request.user.is_staff:
            get_list_or_404(ADSManagerAdministrator, users__in=[request.user])
        return func(request, *args, **kwargs)

    return login_required(wrapped)
