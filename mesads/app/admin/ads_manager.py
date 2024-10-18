from django.contrib import admin
from django.db.models import Count, Q
from django.urls import reverse
from django.utils.safestring import mark_safe

from mesads.fradm.models import Commune, Prefecture, EPCI

from ..models import (
    ADSManager,
    ADSManagerDecree,
)


class ADSCount(admin.SimpleListFilter):
    """Filter by count of ADS."""

    title = "Nombre d'ADS"

    parameter_name = "ads_count"

    def lookups(self, request, model_admin):
        return (
            ("1", ">=1 ADS"),
            ("5", ">=5 ADS"),
            ("10", ">=10 ADS"),
            ("50", ">=50 ADS"),
            ("100", ">=100 ADS"),
        )

    def queryset(self, request, queryset):
        try:
            count_filter = int(self.value())
        except (ValueError, TypeError):
            return queryset

        queryset = queryset.annotate(ads_count=Count("ads"))
        return queryset.filter(ads_count__gte=count_filter)


class ADSManagerRequestCount(admin.SimpleListFilter):
    """Filter by count of ADSManagerRequest."""

    title = "Nombre de gestionnaires"

    parameter_name = "ads_managers_count"

    def lookups(self, request, model_admin):
        return (
            ("no", "Aucun gestionnaire"),
            ("yes", "Au moins un gestionnaire"),
        )

    def queryset(self, request, queryset):
        if not self.value():
            return queryset

        queryset = queryset.annotate(
            ads_manager_request_count=Count(
                "adsmanagerrequest", filter=Q(adsmanagerrequest__accepted=True)
            )
        )
        if self.value() == "yes":
            return queryset.filter(ads_manager_request_count__gte=1)
        return queryset.filter(ads_manager_request_count=0)


class ADSManagerDecreeInline(admin.StackedInline):
    model = ADSManagerDecree
    extra = 0


class AdministrationTypeFilter(admin.SimpleListFilter):
    title = "Type d'administration"
    parameter_name = "content_type"

    def lookups(self, request, model_admin):
        return (
            (
                Commune.ads_managers.field.related_query_name(),
                Commune().type_name().capitalize(),
            ),
            (
                Prefecture.ads_managers.field.related_query_name(),
                Prefecture().type_name().capitalize(),
            ),
            (
                EPCI.ads_managers.field.related_query_name(),
                EPCI().type_name().upper(),
            ),
        )

    def queryset(self, request, queryset):
        if not self.value():
            return queryset
        return queryset.filter(content_type__model=self.value())


@admin.register(ADSManager)
class ADSManagerAdmin(admin.ModelAdmin):
    @admin.display(description="Administration")
    def administration(self, obj):
        return obj.content_object.display_text()

    list_display = (
        "administration",
        "display_ads_manager_request_count",
        "display_ads_count",
    )

    list_filter = (
        ADSCount,
        ADSManagerRequestCount,
        AdministrationTypeFilter,
    )

    ordering = ("commune__libelle",)

    fields = (
        "public_url",
        "administrator",
        "administration",
        "no_ads_declared",
        "epci_delegate",
        "is_locked",
        "ads_manager_administrator_users_link",
        "ads_manager_requests_link",
        "ads_link",
    )

    autocomplete_fields = ("epci_delegate",)

    readonly_fields = (
        "public_url",
        "administrator",
        "administration",
        "ads_manager_administrator_users_link",
        "ads_manager_requests_link",
        "ads_link",
    )

    search_fields = (
        "commune__libelle",
        "prefecture__libelle",
        "epci__name",
    )

    inlines = (ADSManagerDecreeInline,)

    @admin.display(description="Voir sur le site public")
    def public_url(self, obj):
        url = reverse(
            "app.ads-manager.detail",
            kwargs={"manager_id": obj.id},
        )
        return mark_safe(f'<a href="{url}">Cliquer ici</a>')

    @admin.display(description="Gestionnaire configuré ?")
    def display_ads_manager_request_count(self, ads_manager):
        if ads_manager.adsmanagerrequest_set.filter(accepted=True).count():
            return "✅"
        return "❌"

    @admin.display(description="Nombre d'ADS enregistrées")
    def display_ads_count(self, ads_manager):
        """Render a dash if ads_count is zero to improve readability."""
        if ads_manager.no_ads_declared:
            return "L'administration ne gère pas d'ADS"
        elif ads_manager.epci_delegate:
            return (
                f"La gestion des ADS est déléguée à l'EPCI {ads_manager.epci_delegate}"
            )
        return ads_manager.ads_count or "-"

    def get_queryset(self, request):
        req = super().get_queryset(request)
        req = req.annotate(ads_count=Count("ads"))
        return req

    def has_add_permission(self, request, obj=None):
        """ADSManager entries are created with the django command
        load_ads_managers. It should not be possible to create or delete them
        from the admin."""
        return False

    def has_delete_permission(self, request, obj=None):
        """ADSManager entries are created with the django command
        load_ads_managers. It should not be possible to create or delete them
        from the admin."""
        return False

    @admin.display(
        description="Utilisateurs ayant un accès préfecture sur ce gestionnaire"
    )
    def ads_manager_administrator_users_link(self, obj):
        url = (
            reverse("admin:users_user_changelist")
            + f"?adsmanageradministrator={obj.administrator.id}"
        )
        count_staff = obj.administrator.users.filter(is_staff=True).count()
        count_not_staff = obj.administrator.users.filter(is_staff=False).count()
        return mark_safe(
            f"""
            <a href="{url}">Voir les {count_staff + count_not_staff} utilisateurs</a>
            <table>
                <tr>
                    <th>Statut</th>
                    <th>Nombre</th>
                </tr>
                <tr>
                    <td>Équipe MesADS</td>
                    <td>{count_staff}</td>
                </tr>
                <tr>
                    <td>Utilisateurs non privilégiés</td>
                    <td>{count_not_staff}</td>
                </tr>
            </table>
        """
        )

    @admin.display(description="Demandes pour gérer les ADS de ce gestionnaire")
    def ads_manager_requests_link(self, obj):
        url = (
            reverse("admin:app_adsmanagerrequest_changelist") + f"?ads_manager={obj.id}"
        )
        accepted = obj.adsmanagerrequest_set.filter(accepted=True).count()
        pending = obj.adsmanagerrequest_set.filter(accepted=None).count()
        refused = obj.adsmanagerrequest_set.filter(accepted=False).count()
        return mark_safe(
            f"""
            <a href="{url}">Voir les {accepted + pending + refused} demandes</a>
            <table>
                <tr>
                    <th>Statut</th>
                    <th>Nombre</th>
                </tr>
                <tr>
                    <td>⏰ En attente</td>
                    <td>{pending}</td>
                </tr>
                <tr>
                    <td>✅ Acceptées</td>
                    <td>{accepted}</td>
                </tr>
                <tr>
                    <td>❌ Refusées</td>
                    <td>{refused}</td>
                </tr>
            </table>
        """
        )

    @admin.display(description="Liste des ADS du gestionnaire")
    def ads_link(self, obj):
        url = reverse("admin:app_ads_changelist") + f"?ads_manager={obj.id}"
        return mark_safe(f'<a href="{url}">Voir les {obj.ads_count} ADS</a>')
