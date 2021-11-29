from django.contrib import admin

from .models import ADS, ADSManager, ADSManagerAdministrator


@admin.register(ADSManager)
class ADSManagerAdmin(admin.ModelAdmin):
    list_display = (
        'content_type',
        'content_object',
    )

    search_fields = (
        'content_type',
        'content_object',
    )


class ADSManagerInline(admin.TabularInline):
    model = ADSManagerAdministrator.ads_managers.through

    readonly_fields = (
        'adsmanager',
    )

    def get_queryset(self, request):
        req = super().get_queryset(request)
        req = req.prefetch_related('adsmanager__content_type')
        req = req.prefetch_related('adsmanager__content_object')
        return req

    def has_add_permission(self, request, obj=None):
        """Do not allow to add a new ADSManager from the admin interface: this
        should be done with the admin command `load_ads_managers`.
        """
        return False

    def has_delete_permission(self, request, obj=None):
        """Do not allow to remove ADSManager from the admin interface: this
        should be done with the admin command `load_ads_managers`.
        """
        return False


@admin.register(ADSManagerAdministrator)
class ADSManagerAdministratorAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        req = super().get_queryset(request)
        req = req.prefetch_related('prefecture')
        return req

    inlines = (
        ADSManagerInline,
    )

    # ads_managers is rendered by ADSManagerInline.
    exclude = ('ads_managers',)


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
