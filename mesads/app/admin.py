from django.contrib import admin
from django.contrib.auth.models import Group

from .models import ADS, ADSManager, ADSManagerAdministrator, ADSManagerRequest


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

    fields = (
        'number',
        'owner_firstname',
        'owner_lastname',
        'immatriculation_plate',
        'user_name',
    )


@admin.register(ADSManager)
class ADSManagerAdmin(admin.ModelAdmin):
    list_display = (
        lambda ads_manager: ads_manager.content_type.name,
        'content_object',
    )

    fields = (
        'content_type',
        'object_id',
    )

    readonly_fields = (
        'content_type',
        'object_id',
    )

    search_fields = (
        'commune__libelle',
        'prefecture__libelle',
        'epci__name',
    )

    inlines = (
        ADSInline,
    )

    def get_queryset(self, request):
        req = super().get_queryset(request)
        req = req.prefetch_related('content_type')
        req = req.prefetch_related('content_object')
        return req

    def has_add_permission(self, request, obj=None):
        """Added by command load_ads_managers."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Added by command load_ads_managers."""
        return False


class ADSManagerInline(ReadOnlyInline):
    model = ADSManagerAdministrator.ads_managers.through

    fields = (
        'adsmanager',
    )

    def get_queryset(self, request):
        req = super().get_queryset(request)
        req = req.prefetch_related('adsmanager__content_type')
        req = req.prefetch_related('adsmanager__content_object')
        return req


class ADSManagerAdministratorUsersInline(admin.TabularInline):
    model = ADSManagerAdministrator.users.through


@admin.register(ADSManagerAdministrator)
class ADSManagerAdministratorAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        req = super().get_queryset(request)
        req = req.prefetch_related('prefecture')
        return req

    inlines = (
        ADSManagerInline,
        ADSManagerAdministratorUsersInline,
    )

    fields = (
        'prefecture',
    )

    readonly_fields = (
        'prefecture',
    )

    search_fields = (
        'prefecture__libelle',
    )

    # ads_managers is rendered by ADSManagerInline.
    exclude = ('ads_managers',)

    def has_add_permission(self, request, obj=None):
        """Added by command load_ads_managers."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Added by command load_ads_managers."""
        return False


@admin.register(ADSManagerRequest)
class ADSManagerRequestAdmin(admin.ModelAdmin):
    autocomplete_fields = ('ads_manager',)

    list_display = ('created_at', 'user', 'administration', 'accepted')
    ordering = ('-created_at',)
    list_filter = ('accepted',)

    @admin.display
    def administration(self, ads_manager_request):
        return ads_manager_request.ads_manager.content_object.display_text()

    def get_queryset(self, request):
        req = super().get_queryset(request)
        req = req.prefetch_related('user')
        req = req.prefetch_related('ads_manager__content_type')
        req = req.prefetch_related('ads_manager__content_object')
        return req


@admin.register(ADS)
class ADSAdmin(admin.ModelAdmin):
    list_display = (
        'ads_manager',
        'number',
        'ads_creation_date',
        'attribution_date',
        'immatriculation_plate',
        'owner_firstname',
        'owner_lastname',
        'user_name',
    )

    search_fields = (
        'immatriculation_plate__iexact',
        'number__istartswith',
    )

    autocomplete_fields = (
        'ads_manager',
    )

    def get_queryset(self, request):
        req = super().get_queryset(request)
        req = req.prefetch_related('ads_manager__content_type')
        req = req.prefetch_related('ads_manager__content_object')
        return req
