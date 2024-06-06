from django.contrib import admin

from mesads.app.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    autocomplete_fields = ("user",)

    list_display = (
        "user",
        "ads_manager_requests",
    )
