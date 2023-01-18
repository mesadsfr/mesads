from django.contrib import admin
from django.contrib.auth.models import Group
from django.db.models import Count

from reversion.admin import VersionAdmin

from .models import (
    ADS,
    ADSLegalFile,
    ADSManager,
    ADSManagerAdministrator,
    ADSManagerRequest,
    ADSUpdateFile,
    ADSUser,
)


# Remove "Group" administration from admin. We do not use groups in the
# application.
admin.site.unregister(Group)


class ReadOnlyInline(admin.TabularInline):
    """Inline table which doesn't allow to add, update or delete rows."""

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return list(super().get_fields(request, obj))


class ADSInline(ReadOnlyInline):
    """ADS can be created, deleted or changed from ADSAdmin. This inline is
    read only."""
    model = ADS
    show_change_link = True

    fields = (
        'number',
        'owner_name',
        'immatriculation_plate',
    )


@admin.register(ADSManager)
class ADSManagerAdmin(admin.ModelAdmin):

    @admin.display(description='Administration')
    def administration(self, obj):
        return obj.content_object.display_text()

    list_display = (
        'administration',
        'display_ads_count',
    )

    fields = (
        'administrator',
        'administration',
        'display_ads_count',
        'no_ads_declared',
        'is_locked',
    )

    readonly_fields = (
        'administrator',
        'administration',
        'display_ads_count',
    )

    search_fields = (
        'commune__libelle',
        'prefecture__libelle',
        'epci__name',
    )

    inlines = (
        ADSInline,
    )

    @admin.display(description='Nombre d\'ADS enregistrées')
    def display_ads_count(self, ads_manager):
        """Render a dash if ads_count is zero to improve readability."""
        return ads_manager.ads_count or '-'

    def get_queryset(self, request):
        req = super().get_queryset(request)
        req = req.prefetch_related('content_object')
        req = req.annotate(ads_count=Count('ads'))
        return req

    def has_add_permission(self, request, obj=None):
        """Added by command load_ads_managers."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Added by command load_ads_managers."""
        return False


class ADSManagerAdministratorUsersInline(admin.TabularInline):
    model = ADSManagerAdministrator.users.through


@admin.register(ADSManagerAdministrator)
class ADSManagerAdministratorAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        req = super().get_queryset(request)
        req = req.select_related('prefecture')
        req = req.prefetch_related('adsmanager_set')
        req = req.annotate(ads_count=Count('adsmanager__ads'))
        return req

    list_display = (
        '__str__',
        'display_ads_count',
        'expected_ads_count',
    )

    inlines = (
        ADSManagerAdministratorUsersInline,
    )

    fields = (
        'prefecture',
        'expected_ads_count',
        'display_ads_count',
    )

    readonly_fields = (
        'prefecture',
        'display_ads_count',
    )

    search_fields = (
        'prefecture__libelle',
    )

    @admin.display(description='Nombre d\'ADS enregistrées')
    def display_ads_count(self, ads_manager_administrator):
        return ads_manager_administrator.ads_count or '-'

    def has_add_permission(self, request, obj=None):
        """Added by command load_ads_managers."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Added by command load_ads_managers."""
        return False


@admin.register(ADSManagerRequest)
class ADSManagerRequestAdmin(VersionAdmin):
    autocomplete_fields = ('ads_manager',)

    list_display = ('created_at', 'user', 'administration', 'accepted')
    ordering = ('-created_at',)
    list_filter = ('accepted',)
    search_fields = ('user__email__icontains',)

    @admin.display(description='Administration')
    def administration(self, ads_manager_request):
        return ads_manager_request.ads_manager.content_object.display_text()

    def get_queryset(self, request):
        req = super().get_queryset(request)
        req = req.prefetch_related('user')
        req = req.prefetch_related('ads_manager__content_type')
        req = req.prefetch_related('ads_manager__content_object')
        return req


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


@admin.register(ADSUpdateFile)
class ADSUpdateFileAdmin(admin.ModelAdmin):

    ordering = ('-creation_date',)

    list_display = (
        'creation_date',
        'user',
        'imported',
    )

    list_filter = (
        'imported',
    )
