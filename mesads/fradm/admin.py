from django.contrib import admin

from .models import Commune, Prefecture


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
