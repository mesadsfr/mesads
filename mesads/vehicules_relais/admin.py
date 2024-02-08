from django.contrib import admin
from django.db.models import Count
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import Vehicule, Proprietaire


class UsersInline(admin.TabularInline):
    model = Proprietaire.users.through
    autocomplete_fields = ["user"]


class VehiculeCount(admin.SimpleListFilter):
    """Filter by vehicules count."""

    title = "Nombre de véhicules"

    parameter_name = "vehicules_count"

    def lookups(self, request, model_admin):
        return (
            ("1", ">=1 véhicule"),
            ("5", ">=5 véhicules"),
            ("10", ">=10 véhicules"),
            ("50", ">=50 véhicules"),
        )

    def queryset(self, request, queryset):
        try:
            count_filter = int(self.value())
        except (ValueError, TypeError):
            return queryset

        queryset = queryset.annotate(vehicule_count=Count("vehicule"))
        return queryset.filter(vehicule_count__gte=count_filter)


@admin.register(Proprietaire)
class ProprietaireAdmin(admin.ModelAdmin):
    list_display = (
        "nom",
        "siret",
        "created_at",
        "last_update_at",
        "display_vehicule_count",
    )

    search_fields = (
        "nom",
        "siret",
        "users__email",
    )

    fields = (
        "created_at",
        "last_update_at",
        "deleted_at",
        "nom",
        "siret",
        "telephone",
        "email",
        "vehicules_link",
    )

    readonly_fields = (
        "created_at",
        "last_update_at",
        "vehicules_link",
    )

    list_filter = (VehiculeCount,)

    inlines = (UsersInline,)

    def get_queryset(self, request):
        qs = Proprietaire.with_deleted.get_queryset()
        qs = qs.annotate(vehicule_count=Count("vehicule"))
        return qs

    @admin.display(description="Nombre de véhicules enregistrés")
    def display_vehicule_count(self, ads_manager):
        return ads_manager.vehicule_count or "-"

    @admin.display(description="Véhicules enregistrés")
    def vehicules_link(self, obj):
        url = (
            reverse("admin:vehicules_relais_vehicule_changelist")
            + f"?proprietaire={obj.id}"
        )
        return mark_safe(f'<a href="{url}">Voir les {obj.vehicule_count} véhicules</a>')


@admin.register(Vehicule)
class VehiculeAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return Vehicule.with_deleted.get_queryset()

    list_display = (
        "proprietaire",
        "departement",
        "numero",
        "created_at",
        "last_update_at",
    )

    fields = (
        "created_at",
        "last_update_at",
        "deleted_at",
        "proprietaire",
        "departement",
        "numero",
        "immatriculation",
        "modele",
        "motorisation",
        "date_mise_circulation",
        "nombre_places",
        "pmr",
        "commune_localisation",
    )

    readonly_fields = (
        "created_at",
        "last_update_at",
        "numero",
    )

    search_fields = (
        "proprietaire",
        "departement",
        "commune_localisation",
    )

    autocomplete_fields = (
        "proprietaire",
        "departement",
        "commune_localisation",
    )
