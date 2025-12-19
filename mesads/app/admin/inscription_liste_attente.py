from django.contrib import admin
from reversion_compare.admin import CompareVersionAdmin

from ..models import InscriptionListeAttente


class InscriptionDeletedFilter(admin.SimpleListFilter):
    title = "Status"
    parameter_name = "deleted"

    def lookups(self, request, model_admin):
        return (
            ("active", "Inscriptions actives"),
            ("deleted", "Inscriptions archivées"),
        )

    def queryset(self, request, queryset):
        if self.value() == "active":
            return queryset.filter(deleted_at__isnull=True)
        if self.value() == "deleted":
            return queryset.filter(deleted_at__isnull=False)
        return queryset


@admin.register(InscriptionListeAttente)
class InscriptionListeAttenteAdmin(CompareVersionAdmin):
    @admin.display(description="Préfecture")
    def prefecture(self, ads):
        return ads.ads_manager.administrator.prefecture.libelle

    @admin.display(description="Administration")
    def administration(self, ads):
        s = ads.ads_manager.content_object.display_text()
        # Capitalize first letter. No-op if string is empty.
        return s[0:1].upper() + s[1:]

    def has_change_permission(self, request, obj=None):
        if obj and obj.ads_manager.is_locked:
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        if obj and obj.ads_manager.is_locked:
            return False
        return True

    @admin.display(description="Numéro de l'ADS")
    def number_with_deleted_info(self, obj):
        return f"{obj.numero}{' (archivée)' if obj.deleted_at else ''}"

    list_display = (
        "number_with_deleted_info",
        "date_creation",
        "administration",
        "prefecture",
        "nom",
        "prenom",
        "email",
        "numero_licence",
    )

    search_fields = (
        "email__icontains",
        "numero_licence__icontains",
        "nom__icontains",
        "prenom__icontains",
    )

    autocomplete_fields = ("ads_manager",)

    list_filter = [
        InscriptionDeletedFilter,
    ]

    def get_queryset(self, request):
        req = InscriptionListeAttente.with_deleted
        req = req.prefetch_related("ads_manager__content_type")
        req = req.prefetch_related("ads_manager__content_object")
        req = req.prefetch_related("ads_manager__administrator__prefecture")
        return req
