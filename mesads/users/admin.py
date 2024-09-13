from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm
from django.db.models import Count, F, Q
from django.db.models.functions import Collate
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe


from mesads.app.models import Notification

from .models import User


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
    )

    readonly_fields = (
        "date_joined",
        "last_login",
        "admin_roles_link",
        "ads_manager_request_link",
        "notifications_link",
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
        """Users should not be deleted. To deactivate a user, we can simply set
        the flag is_active to False.

        In the future, we can consider allowing the deletion of users if they
        have no related data.
        """
        return False
