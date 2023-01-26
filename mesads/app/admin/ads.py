from django.contrib import admin

from reversion.admin import VersionAdmin

from ..models import (
    ADS,
    ADSLegalFile,
    ADSUser,
)


class ADSUserInline(admin.TabularInline):
    model = ADSUser
    extra = 0
    verbose_name = 'Exploitant de l\'ADS'
    verbose_name_plural = 'Exploitants de l\'ADS'


class ADSLegalFileInline(admin.StackedInline):
    model = ADSLegalFile
    extra = 0


@admin.register(ADS)
class ADSAdmin(VersionAdmin):

    @admin.display(description='Administration')
    def administration(self, ads):
        return ads.ads_manager.content_object.display_text()

    def has_change_permission(self, request, obj=None):
        if obj and obj.ads_manager.is_locked:
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        if obj and obj.ads_manager.is_locked:
            return False
        return True

    list_display = (
        'administration',
        'number',
        'ads_creation_date',
        'attribution_date',
        'immatriculation_plate',
        'owner_name',
    )

    search_fields = (
        'immatriculation_plate__iexact',
        'number__istartswith',
    )

    autocomplete_fields = (
        'ads_manager',
        'epci_commune',
    )

    inlines = [
        ADSUserInline,
        ADSLegalFileInline,
    ]

    def get_queryset(self, request):
        req = super().get_queryset(request)
        req = req.prefetch_related('ads_manager__content_type')
        req = req.prefetch_related('ads_manager__content_object')
        return req
