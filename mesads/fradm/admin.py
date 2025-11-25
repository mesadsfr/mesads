from django.contrib import admin
from django.db import transaction
from mesads.app.models import ADSManager
from .forms import AeroportAdminForm
from .models import Commune, EPCI, Prefecture, Aeroport


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


@admin.register(Aeroport)
class AeroportAdmin(admin.ModelAdmin):
    form = AeroportAdminForm

    list_display = (
        "name",
        "departement",
    )

    search_fields = (
        "name__icontains",
        "departement__istartswith",
    )

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        prefecture = form.cleaned_data.get("prefecture")

        if change:
            if obj.departement != prefecture.numero:
                ads_manager = obj.ads_managers.first()
                ads_manager.administrator = prefecture.adsmanageradministrator
                ads_manager.save()
                obj.departement = prefecture.numero
            obj.name = form.cleaned_data.get("name")
            obj.save()
            return

        aeroport = Aeroport.objects.create(
            name=form.cleaned_data.get("name"), departement=prefecture.numero
        )
        ADSManager.objects.create(
            administrator=prefecture.adsmanageradministrator, content_object=aeroport
        )
