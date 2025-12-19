import csv

from django.contrib import admin
from django.db.models import F, Q
from django.db.models.functions import Collate
from django.http import HttpResponse
from reversion.admin import VersionAdmin

from ..models import (
    ADSManagerRequest,
)


@admin.register(ADSManagerRequest)
class ADSManagerRequestAdmin(VersionAdmin):
    autocomplete_fields = ("ads_manager", "user")

    list_display = (
        "created_at",
        "user",
        "administration",
        "accepted",
    )
    ordering = ("-created_at",)
    list_filter = ("accepted", "user__is_active")
    search_fields = ("user__email",)

    fields = (
        "user",
        "ads_manager",
        "accepted",
        "created_at",
        "last_update_at",
    )

    readonly_fields = (
        "created_at",
        "last_update_at",
    )

    actions = ["download_as_csv"]

    def download_as_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=demandes d'accès.csv"
        writer = csv.writer(response)
        writer.writerow(
            [
                "Date de la demande",
                "Email",
                "Identifiant du gestionnaire ADS",
                "Nom du gestionnaire",
                "Statut de la demande",
                "Dernière mise à jour",
            ]
        )
        for obj in queryset:
            writer.writerow(
                [
                    obj.created_at,
                    obj.user.email,
                    obj.ads_manager.id,
                    obj.ads_manager.content_object.display_text(),
                    {True: "Acceptée", False: "Rejetée", None: "Sans réponse"}[
                        obj.accepted
                    ],
                    obj.last_update_at,
                ]
            )
        return response

    download_as_csv.short_description = "Télécharger la sélection au format CSV"

    def get_search_results(self, request, queryset, search_term):
        """The field Users.email uses a non-deterministic collation, which makes
        it impossible to perform a LIKE query on it.

        By overriding this method, we can specify the collation to use for the search.
        """
        use_distinct = True
        queryset = queryset.annotate(collated_email=Collate(F("user__email"), "C"))
        queryset = queryset.filter(
            Q(
                collated_email__icontains=search_term,
            )
        )
        return (
            queryset,
            use_distinct,
        )

    @admin.display(description="Administration")
    def administration(self, ads_manager_request):
        return ads_manager_request.ads_manager.content_object.display_text()

    def get_queryset(self, request):
        req = super().get_queryset(request)
        req = req.prefetch_related("user")
        req = req.prefetch_related("ads_manager__content_type")
        req = req.prefetch_related("ads_manager__content_object")
        return req
