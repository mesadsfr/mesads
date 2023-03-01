from django.contrib import admin
from django.db.models import Count
from django.urls import reverse
from django.utils.safestring import mark_safe

from ..models import (
    ADSManager,
    ADSManagerDecree,
)


class ADSManagerDecreeInline(admin.StackedInline):
    model = ADSManagerDecree
    extra = 0


@admin.register(ADSManager)
class ADSManagerAdmin(admin.ModelAdmin):

    @admin.display(description='Administration')
    def administration(self, obj):
        return obj.content_object.display_text()

    list_display = (
        'administration',
        'display_ads_count',
    )

    fields = (
        'administrator',
        'administration',
        'no_ads_declared',
        'is_locked',
        'ads_manager_requests_link',
        'ads_link',
    )

    readonly_fields = (
        'administrator',
        'administration',
        'ads_manager_requests_link',
        'ads_link',
    )

    search_fields = (
        'commune__libelle',
        'prefecture__libelle',
        'epci__name',
    )

    inlines = (
        ADSManagerDecreeInline,
    )

    @admin.display(description='Nombre d\'ADS enregistrées')
    def display_ads_count(self, ads_manager):
        """Render a dash if ads_count is zero to improve readability."""
        return ads_manager.ads_count or '-'

    def get_queryset(self, request):
        req = super().get_queryset(request)
        req = req.annotate(ads_count=Count('ads'))
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

    @admin.display(description='Demandes pour gérer les ADS de ce gestionnaire')
    def ads_manager_requests_link(self, obj):
        url = reverse('admin:app_adsmanagerrequest_changelist') + '?ads_manager=' + str(obj.id)

        accepted = obj.adsmanagerrequest_set.filter(accepted=True).count()
        pending = obj.adsmanagerrequest_set.filter(accepted=None).count()
        refused = obj.adsmanagerrequest_set.filter(accepted=False).count()
        return mark_safe(
            f'''<a href="{url}">Voir les {accepted + pending + refused} demandes</a>
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
        ''')

    @admin.display(description='Liste des ADS du gestionnaire')
    def ads_link(self, obj):
        ads_url = reverse('admin:app_ads_changelist') + '?ads_manager=' + str(obj.id)
        return mark_safe(f'<a href="{ads_url}">Voir les {obj.ads_count} ADS</a>')
