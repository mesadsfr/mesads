from django.contrib import admin

from mesads.app.models import WaitingList


@admin.register(WaitingList)
class WaitingListAdmin(admin.ModelAdmin):
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

    fields = (
        "last_update",
        "used_ads_two_years",
        "ads_manager",
        "number",
        "name",
        "license_number",
        "phone_number",
        "email",
        "address",
        "initial_request_date",
        "last_renew_date",
        "end_validity_date",
        "comment",
    )

    readonly_fields = ("last_update", "ads_manager")

    autocomplete_fields = ("ads_manager",)
