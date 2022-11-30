from django.utils.html import format_html
from django.contrib import admin

from .models import User


class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'admin_roles')

    readonly_fields = ('date_joined', 'last_login',)
    fields = ('email', 'date_joined', 'last_login', 'is_superuser', 'is_staff', 'is_active',)
    search_fields = ('email', 'adsmanageradministrator__prefecture__libelle',)

    def get_queryset(self, request):
        req = super().get_queryset(request)
        req = req.prefetch_related('adsmanageradministrator_set__prefecture')
        return req

    def admin_roles(self, user):
        roles = user.adsmanageradministrator_set.all()
        return format_html('<br />'.join(str(role) for role in roles))

    def has_add_permission(self, request, obj=None):
        return False


admin.site.register(User, UserAdmin)
