from django.contrib import admin
from django.db.models import Count
from django.urls import reverse
from django.utils.safestring import mark_safe

from ..models import (
    ADSManagerAdministrator,
)


class ADSManagerAdministratorUsersInline(admin.TabularInline):
    model = ADSManagerAdministrator.users.through
    autocomplete_fields = ["user"]


@admin.register(ADSManagerAdministrator)
class ADSManagerAdministratorAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        req = super().get_queryset(request)
        req = req.select_related("prefecture")
        req = req.prefetch_related("adsmanager_set")
        req = req.annotate(ads_count=Count("adsmanager__ads"))
        return req

    ordering = ("prefecture__numero",)

    list_display = (
        "__str__",
        "display_users_count",
        "display_ads_count",
        "expected_ads_count",
    )

    inlines = (ADSManagerAdministratorUsersInline,)

    fields = (
        "prefecture",
        "expected_ads_count",
        "ads_managers_link",
        "display_ads_count",
    )

    readonly_fields = (
        "prefecture",
        "ads_managers_link",
        "display_ads_count",
    )

    search_fields = ("prefecture__libelle",)

    @admin.display(description="Administrateurs (sans staff MesADS)")
    def display_users_count(self, ads_manager_administrator):
        return ads_manager_administrator.users.filter(is_staff=False).count() or "-"

    @admin.display(description="Nombre d'ADS enregistrées")
    def display_ads_count(self, ads_manager_administrator):
        return ads_manager_administrator.ads_count or "-"

    def has_add_permission(self, request, obj=None):
        """Added by command load_ads_managers."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Added by command load_ads_managers."""
        return False

    @admin.display(description="Liste des gestionnaires d'ADS")
    def ads_managers_link(self, obj):
        ads_managers_url = (
            reverse("admin:app_adsmanager_changelist") + "?administrator=" + str(obj.id)
        )
        return mark_safe(
            f'<a href="{ads_managers_url}">Voir les {obj.adsmanager_set.count()} gestionnaires ADS</a>'
        )
