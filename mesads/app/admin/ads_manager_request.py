from django.contrib import admin

from reversion.admin import VersionAdmin

from ..models import (
    ADSManagerRequest,
)


@admin.register(ADSManagerRequest)
class ADSManagerRequestAdmin(VersionAdmin):
    autocomplete_fields = ("ads_manager",)

    list_display = ("created_at", "user", "administration", "accepted")
    ordering = ("-created_at",)
    list_filter = ("accepted",)
    search_fields = ("user__email__icontains",)

    @admin.display(description="Administration")
    def administration(self, ads_manager_request):
        return ads_manager_request.ads_manager.content_object.display_text()

    def get_queryset(self, request):
        req = super().get_queryset(request)
        req = req.prefetch_related("user")
        req = req.prefetch_related("ads_manager__content_type")
        req = req.prefetch_related("ads_manager__content_object")
        return req
