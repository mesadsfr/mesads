from django.contrib import admin

from ..models import (
    ADSUpdateFile,
)


@admin.register(ADSUpdateFile)
class ADSUpdateFileAdmin(admin.ModelAdmin):
    ordering = ("-creation_date",)

    list_display = (
        "creation_date",
        "user",
        "imported",
    )

    autocomplete_fields = ("user",)

    list_filter = ("imported",)

    readonly_fields = (
        "imported",
        "import_output",
    )
