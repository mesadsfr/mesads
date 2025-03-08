from datetime import date

from django.contrib import admin
from django.db.models import Count
from django.urls import reverse
from django.utils.safestring import mark_safe

from reversion_compare.admin import CompareVersionAdmin

from ..models import (
    ADS,
    ADSLegalFile,
    ADSUser,
)


class ADSPeriodListFilter(admin.SimpleListFilter):
    """Filter ADS by creation date: before or after 2014/10/01."""

    title = "Date de création de l'ADS"

    parameter_name = "ads_period"

    def lookups(self, request, model_admin):
        return (
            ("before", "Avant le 01/10/2014"),
            ("after", "Après le 01/10/2014"),
        )

    def queryset(self, request, queryset):
        if self.value() == "before":
            return queryset.filter(
                ads_creation_date__lt=date(2014, 10, 1),
            )
        elif self.value() == "after":
            return queryset.filter(
                ads_creation_date__gte=date(2014, 10, 1),
            )


class ADSUsersCount(admin.SimpleListFilter):
    """Filter ADS by number of ADSUsers."""

    title = "Nombre d'exploitants"

    parameter_name = "ads_users_count"

    def lookups(self, request, model_admin):
        return (
            ("none", "Aucun exploitant"),
            ("one_plus", ">=1 exploitants"),
            ("two_plus", ">=2 exploitants"),
            ("five_plus", ">=5 exploitants"),
            ("ten_plus", ">=10 exploitants"),
        )

    def queryset(self, request, queryset):
        queryset = queryset.annotate(ads_users_count=Count("adsuser"))
        filters = {
            "one_plus": 1,
            "two_plus": 2,
            "five_plus": 5,
            "ten_plus": 10,
        }
        filter_param = filters.get(self.value())
        if filter_param is None:
            return queryset
        return queryset.filter(ads_users_count__gte=filter_param)


class ADSUserInline(admin.TabularInline):
    model = ADSUser
    extra = 0
    verbose_name = "Exploitant de l'ADS"
    verbose_name_plural = "Exploitants de l'ADS"


class ADSLegalFileInline(admin.StackedInline):
    model = ADSLegalFile
    extra = 0


class ADSDeletedFilter(admin.SimpleListFilter):
    title = "Status"
    parameter_name = "deleted"

    def lookups(self, request, model_admin):
        return (
            ("active", "ADS valides"),
            ("deleted", "ADS supprimées"),
        )

    def queryset(self, request, queryset):
        if self.value() == "active":
            return queryset.filter(deleted_at__isnull=True)
        if self.value() == "deleted":
            return queryset.filter(deleted_at__isnull=False)
        return queryset


@admin.register(ADS)
class ADSAdmin(CompareVersionAdmin):
    @admin.display(description="Préfecture")
    def prefecture(self, ads):
        return ads.ads_manager.administrator.prefecture.libelle

    @admin.display(description="Administration")
    def administration(self, ads):
        s = ads.ads_manager.content_object.display_text()
        # Capitalize first letter. No-op if string is empty.
        return s[0:1].upper() + s[1:]

    @admin.display(description="Exploitants")
    def ads_users(self, ads):
        """It is not easy to customize django administration. To override the
        results table, we need to:

        - override django/contrib/admin/templates/admin/change_list.html (which
          renders change_list_results.html)
        - or override
          django.contrib.admin.templatetags.admin_list.change_list_results
          (which renders change_list_results.html)

        Instead, we do the following. It is not ideal, but it works.
        """
        ads_users = ads.adsuser_set.all()
        if not ads_users:
            return "-"

        content = ""
        for ads_user in ads_users:
            content += f"""
                <tr>
                    <td>{ads_user.status}</td>
                    <td>{ads_user.name}</td>
                    <td>{ads_user.siret}</td>
                    <td>{ads_user.license_number}</td>
                </tr>
            """
        return mark_safe(
            f"""
        <table>
            <tr>
                <th>Statut</th>
                <th>Nom</th>
                <th>SIRET</th>
                <th>Carte pro</th>
            </tr>
            {content}
        </table>
        """
        )

    @admin.display(description="Voir sur le site public")
    def public_url(self, obj):
        url = reverse(
            "app.ads.detail",
            kwargs={"manager_id": obj.ads_manager.id, "ads_id": obj.id},
        )
        return mark_safe(f'<a href="{url}">Cliquer ici</a>')

    def has_change_permission(self, request, obj=None):
        if obj and obj.ads_manager.is_locked:
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        if obj and obj.ads_manager.is_locked:
            return False
        return True

    def get_fields(self, request, obj=None):
        """Set fields to the default value (ie. all fields), and add public_url"""
        fields = super().get_fields(request, obj)
        return ["public_url"] + fields

    @admin.display(description="Numéro de l'ADS")
    def number_with_deleted_info(self, obj):
        return f"{obj.number}{' (supprimée)' if obj.deleted_at else ''}"

    readonly_fields = ("public_url",)

    list_display = (
        "number_with_deleted_info",
        "administration",
        "prefecture",
        "owner_name",
        "owner_siret",
        "ads_users",
        "deleted_at",
    )

    search_fields = (
        "immatriculation_plate__iexact",
        "number__istartswith",
    )

    autocomplete_fields = (
        "ads_manager",
        "epci_commune",
    )

    inlines = [
        ADSUserInline,
        ADSLegalFileInline,
    ]

    list_filter = [
        ADSPeriodListFilter,
        "adsuser__status",
        ADSUsersCount,
        "accepted_cpam",
        "vehicle_compatible_pmr",
        ADSDeletedFilter,
    ]

    def get_queryset(self, request):
        req = ADS.with_deleted
        req = req.prefetch_related("ads_manager__content_type")
        req = req.prefetch_related("ads_manager__content_object")
        req = req.prefetch_related("ads_manager__administrator__prefecture")
        req = req.prefetch_related("adsuser_set")
        return req
