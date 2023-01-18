from django.contrib import admin
from django.contrib.auth.models import Group
from django.db.models import Count
from django.urls import reverse
from django.utils.safestring import mark_safe

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
        'no_ads_declared',
        'is_locked',
        'ads_link',
    )

    readonly_fields = (
        'administrator',
        'administration',
        'ads_link',
    )

    search_fields = (
        'commune__libelle',
        'prefecture__libelle',
        'epci__name',
    )

    @admin.display(description='Nombre d\'ADS enregistrées')
    def display_ads_count(self, ads_manager):
        """Render a dash if ads_count is zero to improve readability."""
        return ads_manager.ads_count or '-'

    def get_queryset(self, request):
        req = super().get_queryset(request)
        req = req.annotate(ads_count=Count('ads'))
        return req

    def has_add_permission(self, request, obj=None):
        """ADSManager entries are created with the django command
        load_ads_managers. It should not be possible to create or delete them
        from the admin."""
        return False

    def has_delete_permission(self, request, obj=None):
        """ADSManager entries are created with the django command
        load_ads_managers. It should not be possible to create or delete them
        from the admin."""
        return False

    @admin.display(description='Liste des ADS du gestionnaire')
    def ads_link(self, obj):
        ads_url = reverse('admin:app_ads_changelist') + '?ads_manager=' + str(obj.id)
        return mark_safe(f'<a href="{ads_url}">Voir les {obj.ads_count} ADS</a>')


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
        'ads_managers_link',
        'display_ads_count',
    )

    readonly_fields = (
        'prefecture',
        'ads_managers_link',
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

    @admin.display(description="Liste des gestionnaires d'ADS")
    def ads_managers_link(self, obj):
        ads_managers_url = reverse('admin:app_adsmanager_changelist') + '?administrator=' + str(obj.id)
        return mark_safe(f'<a href="{ads_managers_url}">Voir les {obj.adsmanager_set.count()} gestionnaires ADS</a>')


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
