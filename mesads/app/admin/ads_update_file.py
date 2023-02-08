from django.contrib import admin

from ..models import (
    ADSUpdateFile,
)


@admin.register(ADSUpdateFile)
class ADSUpdateFileAdmin(admin.ModelAdmin):

    ordering = ('-creation_date',)

    list_display = (
        'creation_date',
        'user',
        'imported',
    )

    list_filter = (
        'imported',
    )

    readonly_fields = (
        'imported',
    )
