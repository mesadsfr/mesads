import csv
from datetime import date, timedelta

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Count, F, Q
from django.db.models.functions import Collate
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from reversion.models import Revision

from mesads.app.models import Notification
from mesads.vehicules_relais.models import Proprietaire

from .models import NoteUtilisateur, User, UserAuditEntry


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
        if self.value() == "yes":
            return queryset.filter(adsmanageradministrator__isnull=False)
        elif self.value() == "no":
            return queryset.filter(adsmanageradministrator__isnull=True)


class ProprietaireFilter(admin.SimpleListFilter):
    title = "Compte propriétaire de taxis relais"

    parameter_name = "with_proprietaire"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Oui"),
            ("no", "Non"),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(
                proprietaire__isnull=False, proprietaire__deleted_at__isnull=True
            )
        elif self.value() == "no":
            return queryset.filter(proprietaire__isnull=True)


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


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    change_list_template = "admin/auth/user/change_list_with_export.html"

    list_display = (
        "date_joined",
        "email",
        "admin_roles",
        "last_login",
        "pro_connect",
        "is_active",
    )

    list_filter = (
        "is_active",
        ADSManagerRequestFilter,
        ADSManagerAdministratorFilter,
        ProprietaireFilter,
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

    def pro_connect(self, obj):
        return bool(obj.proconnect_sub)

    pro_connect.boolean = True
    pro_connect.short_description = "Pro Connect"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "export-gestionnaires/",
                self.admin_site.admin_view(self.export_gestionnaire),
                name=f"{User._meta.app_label}_{User._meta.model_name}_export_gestionnaire",
            ),
        ]
        return custom_urls + urls

    def export_gestionnaire(self, request):
        """
        Vue qui renvoie le CSV des emails des Users reliés à un ADSManager
        via un ADSManagerRequest(accepted=True).
        """
        qs = (
            self.get_queryset(request)
            .filter(adsmanagerrequest__accepted=True, is_active=True)
            .distinct()
            .values_list("email", flat=True)
        )

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            'attachment; filename="users_gestionnaires.csv"'
        )
        writer = csv.writer(response)
        writer.writerow(["email"])
        for user in qs:
            if user:
                writer.writerow([user])
        return response

    def changelist_view(self, request, extra_context=None):
        """
        On passe l’URL du bouton au template.
        """
        extra_context = extra_context or {}
        export_url = reverse(
            f"admin:{User._meta.app_label}_{User._meta.model_name}_export_gestionnaire"
        )
        extra_context["export_ads_accepted_url"] = export_url
        return super().changelist_view(request, extra_context=extra_context)

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
            f'<a href="{ads_manager_request_link}">'
            f"Voir les {obj.adsmanageradministrator_set.count()} "
            "administrateurs des gestionnaires</a>"
        )

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="Requêtes d'accès gestionnaire de cet utilisateur")
    def ads_manager_request_link(self, obj):
        ads_manager_request_link = (
            reverse("admin:app_adsmanagerrequest_changelist") + "?user=" + str(obj.id)
        )
        return mark_safe(
            f'<a href="{ads_manager_request_link}">'
            f"Voir les {obj.adsmanagerrequest_set.count()} "
            "requêtes</a>"
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

        return render_to_string(
            template_name="admin/auth/user/table_proprietaire.html",
            context={"proprietaires": proprietaires},
        )

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


class NoteFaciliteFilter(admin.SimpleListFilter):
    title = "Note facilité"
    parameter_name = "note_facilite"

    def lookups(self, request, model_admin):
        return (
            (1, "1"),
            (2, "2"),
            (3, "3"),
            (4, "4"),
            (5, "5"),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(note_facilite=self.value())
        return queryset


class NoteQualiteFilter(admin.SimpleListFilter):
    title = "Note qualité"
    parameter_name = "note_qualite"

    def lookups(self, request, model_admin):
        return (
            (1, "1"),
            (2, "2"),
            (3, "3"),
            (4, "4"),
            (5, "5"),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(note_qualite=self.value())
        return queryset


@admin.register(NoteUtilisateur)
class NoteUtilisateurAdmin(admin.ModelAdmin):
    @admin.display(description="Utilisateur")
    def utilisateur(self, note):
        return note.user.email

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    list_display = (
        "utilisateur",
        "note_qualite",
        "note_facilite",
    )

    search_fields = ("user__email__icontains",)

    list_filter = [
        NoteQualiteFilter,
        NoteFaciliteFilter,
    ]

    def get_queryset(self, request):
        req = NoteUtilisateur.objects
        req = req.prefetch_related("user")
        req = req.filter(Q(note_facilite__isnull=False) | Q(note_qualite__isnull=False))
        return req
