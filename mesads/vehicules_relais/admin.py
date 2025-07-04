from django.contrib import admin
from django.db.models import Count, F, Q
from django.db.models.functions import Collate
from django.urls import reverse
from django.utils.safestring import mark_safe

from markdownx.admin import MarkdownxModelAdmin

from .models import Vehicule, Proprietaire, DispositionSpecifique


class UsersInline(admin.TabularInline):
    model = Proprietaire.users.through
    autocomplete_fields = ["user"]


class VehiculeCount(admin.SimpleListFilter):
    """Filter by vehicules count."""

    title = "Nombre de véhicules"

    parameter_name = "vehicules_count"

    def lookups(self, request, model_admin):
        return (
            ("0", "Aucun véhicule"),
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
        if count_filter == 0:
            return queryset.filter(vehicule_count=count_filter)
        else:
            return queryset.filter(vehicule_count__gte=count_filter)


class ProprietaireIsDeleted(admin.SimpleListFilter):
    title = "Statut du propriétaire"

    parameter_name = "deleted"

    def lookups(self, request, model_admin):
        return (
            ("oui", "Supprimé"),
            ("non", "Actif"),
        )

    def queryset(self, request, queryset):
        if self.value() == "oui":
            return queryset.exclude(deleted_at__isnull=True)
        if self.value() == "non":
            return queryset.filter(deleted_at__isnull=True)
        return queryset


@admin.register(Proprietaire)
class ProprietaireAdmin(admin.ModelAdmin):
    list_display = (
        "nom",
        "siret",
        "created_at",
        "last_update_at",
        "display_vehicule_count",
        "is_active",
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

    list_filter = (VehiculeCount, ProprietaireIsDeleted)

    inlines = (UsersInline,)

    def get_search_results(self, request, queryset, search_term):
        """The field Users.email uses a non-deterministic collation, which makes
        it impossible to perform a LIKE query on it.

        By overriding this method, we can specify the collation to use for the search.
        """
        use_distinct = True
        queryset = queryset.annotate(collated_email=Collate(F("users__email"), "C"))
        queryset = queryset.filter(
            Q(
                nom__icontains=search_term,
            )
            | Q(
                siret__icontains=search_term,
            )
            | Q(
                collated_email__icontains=search_term,
            )
        )
        return (
            queryset,
            use_distinct,
        )

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

    @admin.display(description="Compte actif")
    def is_active(self, proprietaire):
        if not proprietaire.deleted_at:
            return "✅"
        return "❌"


class VehiculeDeletedAtFilter(admin.SimpleListFilter):
    title = "Filtrer les véhicules supprimés"
    parameter_name = "deleted_at"  # URL query parameter

    def lookups(self, request, model_admin):
        return (
            ("deleted", "Supprimés"),
            ("active", "Actifs"),
        )

    def queryset(self, request, queryset):
        if self.value() == "deleted":
            return queryset.exclude(deleted_at__isnull=True)
        if self.value() == "active":
            return queryset.filter(deleted_at__isnull=True)
        return queryset


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
        "deleted_at",
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
        "proprietaire__nom",
        "proprietaire__siret",
        "departement__numero",
        "departement__libelle",
        "commune_localisation__insee",
        "commune_localisation__libelle",
    )

    autocomplete_fields = (
        "proprietaire",
        "departement",
        "commune_localisation",
    )

    list_filter = ("departement", VehiculeDeletedAtFilter)


@admin.register(DispositionSpecifique)
class DispositionSpecifiqueAdmin(MarkdownxModelAdmin):
    list_display = (
        "departement",
        "short_message",
    )

    def short_message(self, obj):
        return obj.message[:200] + "..." if len(obj.message) > 200 else obj.message

    fields = (
        "departement",
        "message",
    )

    search_fields = (
        "departement__numero",
        "departement__libelle",
    )

    autocomplete_fields = ("departement",)
