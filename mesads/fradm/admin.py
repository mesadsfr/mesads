from django.contrib import admin

from .models import Commune, EPCI, Prefecture


class ReadOnlyModelAdmin(admin.ModelAdmin):
    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Commune)
class CommuneAdmin(ReadOnlyModelAdmin):
    list_display = (
        "insee",
        "libelle",
    )

    search_fields = (
        "insee__istartswith",
        "libelle",
    )


@admin.register(Prefecture)
class PrefectureAdmin(ReadOnlyModelAdmin):
    list_display = (
        "numero",
        "libelle",
    )

    search_fields = (
        "numero__iexact",
        "libelle",
    )


@admin.register(EPCI)
class EPCIAdmin(ReadOnlyModelAdmin):
    list_display = (
        "siren",
        "departement",
        "name",
    )

    search_fields = (
        "siren__startswith",
        "departement__istartswith",
        "name",
    )
