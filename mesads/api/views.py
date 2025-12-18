import importlib.resources
from datetime import timedelta

import shapefile
from django.db.models import (
    BooleanField,
    Count,
    IntegerField,
    OuterRef,
    Subquery,
    Value,
)
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import mixins, permissions, views, viewsets
from rest_framework.response import Response

from mesads.app.models import ADS, ADSManagerAdministrator, ADSUpdateFile, ADSUpdateLog
from mesads.fradm.models import Prefecture

from .serializers import ADSUpdateFileSerializer


class ADSUpdatesViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ADSUpdateFileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ADSUpdateFile.objects.filter(user=self.request.user).order_by(
            "-creation_date"
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


def get_stats_by_prefecture():
    date_limite_completion = timezone.now() - timedelta(
        days=ADSUpdateLog.OUTDATED_LOG_DAYS
    )

    total_ads_qs = (
        ADS.objects.select_related("ads_manager", "ads_manager__administrator")
        .filter(
            ads_manager__administrator=OuterRef("pk"),
        )
        .order_by()
        .values("ads_manager__administrator")
        .annotate(c=Count("pk"))
        .values("c")
    )

    last_log_valid = (
        ADSUpdateLog.objects.filter(
            ads=OuterRef("pk"), update_at__gte=date_limite_completion
        )
        .order_by("-update_at")
        .values("is_complete")[:1]
    )

    completed_ads_qs = (
        ADS.objects.select_related("ads_manager", "ads_manager__administrator")
        .filter(
            ads_manager__administrator=OuterRef("pk"),
        )
        .annotate(last_log_valid=Subquery(last_log_valid, output_field=BooleanField()))
        .filter(last_log_valid=True)
        .order_by()
        .values("ads_manager__administrator")
        .annotate(c=Count("pk"))
        .values("c")
    )

    ads_stats = ADSManagerAdministrator.objects.select_related("prefecture").annotate(
        ads_count=Coalesce(
            Subquery(total_ads_qs, output_field=IntegerField()), Value(0)
        ),
        ads_completed_count=Coalesce(
            Subquery(completed_ads_qs, output_field=IntegerField()), Value(0)
        ),
    )

    stats = {
        ads_manager_administrator.prefecture.numero: {
            "ads_count": ads_manager_administrator.ads_count,
            "expected_ads_count": ads_manager_administrator.expected_ads_count,
            "ads_completee_pourcentage": (
                round(
                    (ads_manager_administrator.ads_completed_count * 100)
                    / ads_manager_administrator.ads_count,
                    1,
                )
                if ads_manager_administrator.ads_count
                else 0
            ),
        }
        for ads_manager_administrator in ads_stats.all()
    }

    vehicules_relais_stats = Prefecture.objects.annotate(count=Count("vehicule"))

    for row in vehicules_relais_stats:
        stats[row.numero]["vehicules_relais_count"] = row.count

    return stats


class StatsGeoJSONPerPrefecture(views.APIView):
    """Exposes a GeoJSON with statistics for each prefecture."""

    def get(self, request):
        stats = get_stats_by_prefecture()

        departements_shpfile = (
            importlib.resources.files("mesads.api.resources")
            / "departements-20140306-100m-shp.zip"
        )
        with shapefile.Reader(departements_shpfile, encoding="latin1") as shp:
            geojson = shp.__geo_interface__
            for feature in geojson["features"]:
                insee_code = feature["properties"]["code_insee"]
                feature["properties"]["ads_count"] = stats.get(insee_code, {}).get(
                    "ads_count", 0
                )
                feature["properties"]["expected_ads_count"] = stats.get(
                    insee_code, {}
                ).get("expected_ads_count", 0)
                feature["properties"]["ads_completee_pourcentage"] = stats.get(
                    insee_code, {}
                ).get("ads_completee_pourcentage", 0)
                feature["properties"]["vehicules_relais_count"] = stats.get(
                    insee_code, {}
                ).get("vehicules_relais_count", 0)

            return Response(geojson)
