from django.contrib import admin
from django.db.models import F, Q
from django.db.models.functions import Collate

from mesads.app.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    autocomplete_fields = ("user",)

    list_display = (
        "user",
        "ads_manager_requests",
    )

    search_fields = ("user__email",)

    def get_search_results(self, request, queryset, search_term):
        """The field Users.email uses a non-deterministic collation, which makes
        it impossible to perform a LIKE query on it.

        By overriding this method, we can specify the collation to use for the search.
        """
        use_distinct = True
        queryset = queryset.annotate(collated_email=Collate(F("user__email"), "C"))
        queryset = queryset.filter(
            Q(
                collated_email__icontains=search_term,
            )
        )
        return (
            queryset,
            use_distinct,
        )
