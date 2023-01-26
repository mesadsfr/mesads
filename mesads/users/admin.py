from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe


from .models import User


class ADSManagerRequestFilter(admin.SimpleListFilter):
    title = "Compte avec une demande pour gérer les ADS"

    parameter_name = 'with_adsmanagerrequest'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Oui'),
            ('no', 'Non'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(
                adsmanagerrequest__isnull=False,
            )
        elif self.value() == 'no':
            return queryset.filter(
                adsmanagerrequest__isnull=True,
            )


class ADSManagerAdministratorFilter(admin.SimpleListFilter):
    title = "Compte administrateur des gestionnaires"

    parameter_name = 'with_adsmanagerrequestadmin'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Oui'),
            ('no', 'Non'),
        )

    def queryset(self, request, queryset):
        from django.db.models import Count
        queryset = queryset.annotate(
            adsmanageradministrator_count=Count('adsmanageradministrator')
        )
        if self.value() == 'yes':
            return queryset.filter(adsmanageradministrator_count__gt=0)
        elif self.value() == 'no':
            return queryset.filter(adsmanageradministrator_count=0)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'admin_roles')
    list_filter = (
        ADSManagerRequestFilter,
        ADSManagerAdministratorFilter,
    )

    fields = (
        'email',
        'date_joined',
        'last_login',
        'is_superuser',
        'is_staff',
        'is_active',
        'ads_manager_request_link',
    )
    readonly_fields = (
        'date_joined',
        'last_login',
        'ads_manager_request_link',
    )
    search_fields = (
        'email',
        'adsmanageradministrator__prefecture__libelle',
    )

    def get_queryset(self, request):
        req = super().get_queryset(request)
        req = req.prefetch_related('adsmanageradministrator_set__prefecture')
        return req

    def admin_roles(self, user):
        roles = user.adsmanageradministrator_set.all()
        return format_html('<br />'.join(str(role) for role in roles))

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="Requêtes d'accès pour cet utilisateur")
    def ads_manager_request_link(self, obj):
        ads_manager_request_link = reverse('admin:app_adsmanagerrequest_changelist') + '?user=' + str(obj.id)
        return mark_safe(f'<a href="{ads_manager_request_link}">Voir les {obj.adsmanagerrequest_set.count()} requêtes</a>')
