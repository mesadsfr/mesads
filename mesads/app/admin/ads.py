from datetime import date

from django.contrib import admin
from django.db.models import F

from reversion.admin import VersionAdmin

from ..models import (
    ADS,
    ADSLegalFile,
    ADSUser,
)


class ADSPeriodListFilter(admin.SimpleListFilter):
    """Filter ADS by creation date: before or after 2014/10/01."""
    title = "Date de création de l'ADS"

    parameter_name = 'ads_period'

    def lookups(self, request, model_admin):
        return (
            ('before', 'Avant le 01/10/2014'),
            ('after', 'Après le 01/10/2014'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'before':
            return queryset.filter(
                ads_creation_date__lt=date(2014, 10, 1),
            )
        elif self.value() == 'after':
            return queryset.filter(
                ads_creation_date__gte=date(2014, 10, 1),
            )


class ADSInvalidCreationOrAttributionDateListFilter(admin.SimpleListFilter):
    title = "ADS avec une date de création ultérieure à la date d'attribution"

    parameter_name = "invalid_creation_or_attribution_date"

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Oui'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            # Filter ADS with a creation date after the attribution date
            return queryset.filter(
                ads_creation_date__gt=F('attribution_date'),
            )
        return queryset


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

    list_filter = [
        ADSPeriodListFilter,
        ADSInvalidCreationOrAttributionDateListFilter,
        'used_by_owner',
        'adsuser__status',
        'attribution_type',
        'accepted_cpam',
    ]

    def get_queryset(self, request):
        req = super().get_queryset(request)
        req = req.prefetch_related('ads_manager__content_type')
        req = req.prefetch_related('ads_manager__content_object')
        return req
