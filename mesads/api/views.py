import importlib.resources

import shapefile

from django.db.models import Count

from rest_framework import mixins, permissions, viewsets, views
from rest_framework.response import Response

from mesads.app.models import ADSManagerAdministrator, ADSUpdateFile
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
    ads_stats = ADSManagerAdministrator.objects.select_related("prefecture").annotate(
        ads_count=Count("adsmanager__ads")
    )

    stats = {
        ads_manager_administrator.prefecture.numero: {
            "ads_count": ads_manager_administrator.ads_count,
            "expected_ads_count": ads_manager_administrator.expected_ads_count,
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
                feature["properties"]["vehicules_relais_count"] = stats.get(
                    insee_code, {}
                ).get("vehicules_relais_count", 0)

            return Response(geojson)
