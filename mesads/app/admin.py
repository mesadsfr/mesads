from django.contrib import admin

from .models import ADS, ADSManager, ADSManagerAdministrator


@admin.register(ADSManager)
class ADSManagerAdmin(admin.ModelAdmin):
    list_display = (
        'id',
    )


@admin.register(ADSManagerAdministrator)
class ADSManagerAdministratorAdmin(admin.ModelAdmin):
    pass


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
