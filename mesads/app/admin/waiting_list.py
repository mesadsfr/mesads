from django.contrib import admin

from mesads.app.models import WaitingList


@admin.register(WaitingList)
class NotificationAdmin(admin.ModelAdmin):

    list_fields = (
        "number",
        "name",
        "initial_request_date",
        "last_update_at",
        "end_validity_date",
    )
    search_fields = (
        "number",
        "name",
    )

    autocomplete_fields = ("ads_manager",)
