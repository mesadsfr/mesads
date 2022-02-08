from django.contrib import admin
from django.contrib.auth.models import Group
from django.db import transaction

from .models import ADS, ADSManager, ADSManagerAdministrator, ADSManagerRequest


# Remove "Group" administration from admin. We do not use groups in the
# application.
admin.site.unregister(Group)


class ReadOnlyInline(admin.TabularInline):
    """Inline table which doesn't allow to add, update or delete rows."""
    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return list(super().get_fields(request, obj))


class ADSInline(ReadOnlyInline):
    """ADS can be created, deleted or changed from ADSAdmin. This inline is
    read only."""
    model = ADS

    fields = (
        'number',
        'owner_firstname',
        'owner_lastname',
        'immatriculation_plate',
        'user_name',
    )


@admin.register(ADSManager)
class ADSManagerAdmin(admin.ModelAdmin):

    @admin.display(description='Administration')
    def administration(self, obj):
        return obj.content_object.display_text()

    list_display = (
        'administration',
    )

    fields = (
        'administration',
    )

    readonly_fields = (
        'administration',
    )

    search_fields = (
        'commune__libelle',
        'prefecture__libelle',
        'epci__name',
    )

    inlines = (
        ADSInline,
    )

    def get_queryset(self, request):
        req = super().get_queryset(request)
        req = req.prefetch_related('content_type')
        req = req.prefetch_related('content_object')
        return req

    def has_add_permission(self, request, obj=None):
        """Added by command load_ads_managers."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Added by command load_ads_managers."""
        return False


class ADSManagerInline(ReadOnlyInline):
    model = ADSManagerAdministrator.ads_managers.through

    @admin.display(description='Administration')
    def administration(self, rel):
        return rel.adsmanager.content_object.display_text()

    fields = (
        'administration',
    )

    readonly_fields = (
        'administration',
    )

    def get_queryset(self, request):
        req = super().get_queryset(request)
        req = req.prefetch_related('adsmanager__content_type')
        req = req.prefetch_related('adsmanager__content_object')
        return req


class ADSManagerAdministratorUsersInline(admin.TabularInline):
    model = ADSManagerAdministrator.users.through


@admin.register(ADSManagerAdministrator)
class ADSManagerAdministratorAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        req = super().get_queryset(request)
        req = req.prefetch_related('prefecture')
        return req

    inlines = (
        ADSManagerInline,
        ADSManagerAdministratorUsersInline,
    )

    fields = (
        'prefecture',
    )

    readonly_fields = (
        'prefecture',
    )

    search_fields = (
        'prefecture__libelle',
    )

    # ads_managers is rendered by ADSManagerInline.
    exclude = ('ads_managers',)

    def has_add_permission(self, request, obj=None):
        """Added by command load_ads_managers."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Added by command load_ads_managers."""
        return False

    def save_related(self, request, form, formsets, change):
        """ADSManagerAdministrator contains a list of users who can accept or
        reject requests to become ADSManager from administrations managed by
        the prefecture.

        When saving users of ADSManagerAdministrator, we create for each of
        them an entry in ADSManagerRequest for each administration depending on
        the prefecture.

        In other words, people working for the prefecture can manage the ADS of
        administrations under the authority of this prefecture.
        """
        super().save_related(request, form, formsets, change)

        with transaction.atomic():
            for ads_manager in form.instance.ads_managers.all():
                # formsets[1] is a list of dict with the keys "user" (user for which we
                # add or remove access) and "DELETE" (True when user is removed)
                #
                # Dictionary is empty if user is not configured for this form row.
                for row in formsets[1].cleaned_data:
                    if not row:
                        continue

                    (ads_manager_request, created) = ADSManagerRequest.objects.get_or_create(
                        user=row['user'],
                        ads_manager=ads_manager
                    )

                    if row['DELETE']:
                        ads_manager_request.delete()
                    elif created:
                        ads_manager_request.accepted = True
                        ads_manager_request.save()


@admin.register(ADSManagerRequest)
class ADSManagerRequestAdmin(admin.ModelAdmin):
    autocomplete_fields = ('ads_manager',)

    list_display = ('created_at', 'user', 'administration', 'accepted')
    ordering = ('-created_at',)
    list_filter = ('accepted',)

    @admin.display(description='Administration')
    def administration(self, ads_manager_request):
        return ads_manager_request.ads_manager.content_object.display_text()

    def get_queryset(self, request):
        req = super().get_queryset(request)
        req = req.prefetch_related('user')
        req = req.prefetch_related('ads_manager__content_type')
        req = req.prefetch_related('ads_manager__content_object')
        return req


@admin.register(ADS)
class ADSAdmin(admin.ModelAdmin):

    @admin.display(description='Administration')
    def administration(self, ads):
        return ads.ads_manager.content_object.display_text()

    list_display = (
        'administration',
        'number',
        'ads_creation_date',
        'attribution_date',
        'immatriculation_plate',
        'owner_firstname',
        'owner_lastname',
        'user_name',
    )

    search_fields = (
        'immatriculation_plate__iexact',
        'number__istartswith',
    )

    autocomplete_fields = (
        'ads_manager',
    )

    def get_queryset(self, request):
        req = super().get_queryset(request)
        req = req.prefetch_related('ads_manager__content_type')
        req = req.prefetch_related('ads_manager__content_object')
        return req
