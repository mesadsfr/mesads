from django.contrib import admin

from .models import ADS, Authority


class AuthorityAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'raison_sociale',
        'type',
        'departement',
    )


admin.site.register(Authority, AuthorityAdmin)


class ADSAdmin(admin.ModelAdmin):
    list_display = (
        'authority',
        'number',
        'immatriculation_plate',
        'owner_firstname',
        'owner_lastname',
        'user_name',
    )


admin.site.register(ADS, ADSAdmin)
