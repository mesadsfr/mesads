from django.contrib.contenttypes.models import ContentType
from django.views.generic.list import ListView

from ..models import (
    ADS,
    ADSManager,
)
from mesads.fradm.models import Prefecture


class DashboardsView(ListView):
    template_name = "pages/ads_register/dashboards.html"

    def get_queryset(self):
        ads_manager_paris = ADSManager.objects.filter(
            content_type=ContentType.objects.get_for_model(Prefecture),
            object_id=Prefecture.objects.filter(numero="75").get().id,
        ).get()

        return (
            ADS.objects.prefetch_related("ads_manager__content_object")
            .exclude(ads_manager=ads_manager_paris)
            .order_by("-last_update")[:1000]
        )
