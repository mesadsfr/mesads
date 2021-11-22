from django.contrib import admin

from .models import Commune


@admin.register(Commune)
class CommuneAdmin(admin.ModelAdmin):
    list_display = (
        'insee',
        'libelle',
    )
