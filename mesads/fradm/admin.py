from django.contrib import admin

from .models import Commune, EPCI, Prefecture


@admin.register(Commune)
class CommuneAdmin(admin.ModelAdmin):
    list_display = (
        'insee',
        'libelle',
    )


@admin.register(Prefecture)
class PrefectureAdmin(admin.ModelAdmin):
    list_display = (
        'numero',
        'libelle',
    )

@admin.register(EPCI)
class EPCIAdmin(admin.ModelAdmin):
    list_display = (
        'siren',
        'departement',
        'name',
    )
