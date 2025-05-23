from datetime import date, timedelta

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm
from django.db.models import Count, F, Q
from django.db.models.functions import Collate
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from reversion.models import Revision

from mesads.app.models import Notification
from mesads.vehicules_relais.models import Proprietaire

from .models import User, UserAuditEntry


class ADSManagerRequestFilter(admin.SimpleListFilter):
    title = "Compte avec une demande pour gérer les ADS"

    parameter_name = "with_adsmanagerrequest"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Oui"),
            ("no", "Non"),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(
                adsmanagerrequest__isnull=False,
            )
        elif self.value() == "no":
            return queryset.filter(
                adsmanagerrequest__isnull=True,
            )


class ADSManagerAdministratorFilter(admin.SimpleListFilter):
    title = "Compte administrateur des gestionnaires"

    parameter_name = "with_adsmanagerrequestadmin"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Oui"),
            ("no", "Non"),
        )

    def queryset(self, request, queryset):
        queryset = queryset.annotate(
            adsmanageradministrator_count=Count("adsmanageradministrator")
        )
        if self.value() == "yes":
            return queryset.filter(adsmanageradministrator_count__gt=0)
        elif self.value() == "no":
            return queryset.filter(adsmanageradministrator_count=0)


class LastLoginFilter(admin.SimpleListFilter):
    title = "Date de la dernière connexion"

    parameter_name = "last_login_date"

    def lookups(self, request, model_admin):
        return (
            ("30", "Moins de 1 mois (30 jours)"),
            ("90", "Moins de 3 mois (90 jours)"),
            ("180", "Moins de 6 mois (180 jours)"),
            ("365", "Moins de 12 mois (365 jours)"),
            ("730", "Moins de 24 mois (730 jours)"),
        )

    def queryset(self, request, queryset):
        try:
            since = int(self.value())
        except TypeError:
            return queryset
        today = date.today()
        return queryset.filter(
            last_login__gte=today - timedelta(days=since),
        )


class UserForm(UserChangeForm):
    """Override the default form to add a custom widget to the email field."""

    class Meta:
        model = User
        fields = "__all__"
        widgets = {"email": forms.TextInput(attrs={"size": 100})}


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserForm

    list_display = (
        "date_joined",
        "email",
        "admin_roles",
        "last_login",
        "is_active",
    )

    list_filter = (
        "is_active",
        ADSManagerRequestFilter,
        ADSManagerAdministratorFilter,
        ("last_login", admin.EmptyFieldListFilter),
        LastLoginFilter,
    )

    fieldsets = []

    ordering = ("email",)

    fields = (
        "email",
        "password",
        "date_joined",
        "last_login",
        "is_superuser",
        "is_staff",
        "is_active",
        "admin_roles_link",
        "ads_manager_request_link",
        "notifications_link",
        "relais_links",
        "audit_entries_link",
        "double_authentication_enabled",
    )

    readonly_fields = (
        "date_joined",
        "last_login",
        "admin_roles_link",
        "ads_manager_request_link",
        "notifications_link",
        # We don't want the flags is_staff and is_superuser to be changed by
        # mistake, so they are read-only. Only a technical administrator can
        # change them.
        "is_staff",
        "is_superuser",
        "relais_links",
        "audit_entries_link",
        "double_authentication_enabled",
    )

    search_fields = (
        "email",
        "adsmanageradministrator__prefecture__libelle",
    )

    def get_search_results(self, request, queryset, search_term):
        """The field Users.email uses a non-deterministic collation, which makes
        it impossible to perform a LIKE query on it.

        By overriding this method, we can specify the collation to use for the search.
        """
        use_distinct = True
        queryset = queryset.annotate(collated_email=Collate(F("email"), "C"))
        queryset = queryset.filter(
            Q(
                collated_email__icontains=search_term,
            )
            | Q(
                adsmanageradministrator__prefecture__libelle__icontains=search_term,
            )
        )
        return (
            queryset,
            use_distinct,
        )

    def get_queryset(self, request):
        req = super().get_queryset(request)
        req = req.prefetch_related("adsmanageradministrator_set__prefecture")
        return req

    def admin_roles(self, user):
        roles = user.adsmanageradministrator_set.all()
        return format_html("<br />".join(str(role) for role in roles))

    @admin.display(description="Compte administrateur des gestionnaires")
    def admin_roles_link(self, obj):
        ads_manager_request_link = (
            reverse("admin:app_adsmanageradministrator_changelist")
            + "?users__in="
            + str(obj.id)
        )
        return mark_safe(
            f'<a href="{ads_manager_request_link}">Voir les {obj.adsmanageradministrator_set.count()} administrateurs des gestionnaires</a>'
        )

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="Requêtes d'accès gestionnaire de cet utilisateur")
    def ads_manager_request_link(self, obj):
        ads_manager_request_link = (
            reverse("admin:app_adsmanagerrequest_changelist") + "?user=" + str(obj.id)
        )
        return mark_safe(
            f'<a href="{ads_manager_request_link}">Voir les {obj.adsmanagerrequest_set.count()} requêtes</a>'
        )

    @admin.display(
        description="Voir les notifications configurées pour cet utilisateur",
    )
    def notifications_link(self, obj):
        try:
            link = reverse(
                "admin:app_notification_change",
                kwargs={"object_id": obj.notification.id},
            )
            return mark_safe(
                f'<a href="{link}">Voir la configuration des notifications</a>'
            )
        except Notification.DoesNotExist:
            link = reverse(
                "admin:app_notification_add",
            )
            return mark_safe(f'<a href="{link}">Configurer les notifications</a>')

    def has_delete_permission(self, request, obj=None):
        """Forbid user deletion if the account is referenced by django
        reversion. To deactivate these users, we can simply set the flag
        is_active to False instead. This is to avoid removing users that are
        linked to important resources."""
        if obj:
            count = Revision.objects.filter(user=obj).count()
            if count:
                return False
        return True

    @admin.display(description="Registre des véhicules relais")
    def relais_links(self, obj):
        proprietaires = Proprietaire.objects.filter(users__in=[obj]).annotate(
            vehicules_count=Count("vehicule")
        )

        ret = """
        <table>
            <thead>
                <tr>
                    <th>Propriétaire</th>
                    <th>Nombre de véhicules</th>
                </tr>
            </thead>
            <tbody>
        """
        if len(proprietaires) == 0:
            ret += """
                <tr>
                    <td colspan="2">Aucun compte propriétaire associé</td>
                </tr>
            """
        else:
            for proprietaire in proprietaires:
                proprietaire_url = reverse(
                    "admin:vehicules_relais_proprietaire_change",
                    kwargs={"object_id": proprietaire.id},
                )
                vehicules_url = (
                    reverse("admin:vehicules_relais_vehicule_changelist")
                    + f"?proprietaire={proprietaire.id}"
                )
                ret += f"""
                    <tr>
                        <td><a href="{proprietaire_url}">{proprietaire.nom}</a></td>
                        <td><a href="{vehicules_url}">Voir le(s) {proprietaire.vehicules_count} véhicule(s)</a></td>
                    </tr>
                """

        ret += """
            </tbody>
        </table>
        """
        return mark_safe(ret)

    @admin.display(description="Historique des connexions")
    def audit_entries_link(self, obj):
        url = (
            reverse("admin:users_userauditentry_changelist")
            + f"?user__id__exact={obj.id}"
        )
        return format_html('<a href="{}">Voir les connexions</a>', url)

    @admin.display(description="Double authentification")
    def double_authentication_enabled(self, obj):
        return obj.otp_secret != ""

    double_authentication_enabled.boolean = True


@admin.register(UserAuditEntry)
class UserAuditEntryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action", "ip", "short_body")
    list_filter = ("action",)
    search_fields = ("ip", "body")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    def short_body(self, obj):
        return obj.body[:75] + "..." if len(obj.body) > 75 else obj.body

    short_body.short_description = "Body"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
