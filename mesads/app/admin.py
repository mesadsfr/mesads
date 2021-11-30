from django.contrib import admin

from .models import ADS, ADSManager, ADSManagerAdministrator


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
        'users',
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


@admin.register(ADSManagerAdministrator)
class ADSManagerAdministratorAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        req = super().get_queryset(request)
        req = req.prefetch_related('prefecture')
        return req

    inlines = (
        ADSManagerInline,
    )

    fields = (
        'prefecture',
        'users',
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


@admin.register(ADS)
class ADSAdmin(admin.ModelAdmin):
    list_display = (
        'ads_manager',
        'number',
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
