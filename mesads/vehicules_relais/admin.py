from django.contrib import admin

from .models import Vehicule, Proprietaire


@admin.register(Proprietaire)
class ProprietaireAdmin(admin.ModelAdmin):
    list_display = (
        "nom",
        "siret",
        "created_at",
        "last_update_at",
    )


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
    )

    readonly_fields = (
        "created_at",
        "last_update_at",
        "numero",
    )
