from django.contrib import admin

from .models import ADS, Registrar


class RegistrarAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'raison_sociale',
        'authority',
        'departement',
    )


admin.site.register(Registrar, RegistrarAdmin)


class ADSAdmin(admin.ModelAdmin):
    list_display = (
        'registrar',
        'number',
        'immatriculation_plate',
        'owner_firstname',
        'owner_lastname',
        'user_name',
    )


admin.site.register(ADS, ADSAdmin)
