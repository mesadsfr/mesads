from django.contrib import admin

from .models import ADS, ADSManager, ADSManagerAdministrator


@admin.register(ADSManager)
class ADSManagerAdmin(admin.ModelAdmin):
    list_display = (
        'entity_type',
        'entity_object',
    )


@admin.register(ADSManagerAdministrator)
class ADSManagerAdministratorAdmin(admin.ModelAdmin):

    def get_queryset(self, request):
        # XXX: find how to lazyload ads_managers to remove raw_id_fields
        req = super().get_queryset(request)
        return req

    raw_id_fields = (
        'ads_managers',
    )
    #readonly_fields = ('ads_managers',)


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
