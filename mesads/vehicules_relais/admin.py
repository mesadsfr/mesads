from django.contrib import admin

from .models import Vehicule, Proprietaire


class UsersInline(admin.TabularInline):
    model = Proprietaire.users.through
    autocomplete_fields = ["user"]


@admin.register(Proprietaire)
class ProprietaireAdmin(admin.ModelAdmin):
    list_display = (
        "nom",
        "siret",
        "created_at",
        "last_update_at",
    )

    search_fields = (
        "nom",
        "siret",
    )

    fields = (
        "created_at",
        "last_update_at",
        "nom",
        "siret",
        "telephone",
        "email",
    )

    readonly_fields = (
        "created_at",
        "last_update_at",
    )

    inlines = (UsersInline,)


@admin.register(Vehicule)
class VehiculeAdmin(admin.ModelAdmin):
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
        "localisation",
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
