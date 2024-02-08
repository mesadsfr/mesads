import importlib.resources

import shapefile

from django.db.models import Count

from rest_framework import mixins, permissions, viewsets, views
from rest_framework.response import Response

from mesads.app.models import ADSManagerAdministrator, ADSUpdateFile

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


class StatsGeoJSONPerPrefecture(views.APIView):
    """Exposes a GeoJSON with the number of ADS for each prefecture."""

    def get(self, request):
        query_stats = ADSManagerAdministrator.objects.select_related(
            "prefecture"
        ).annotate(ads_count=Count("adsmanager__ads"))

        stats = {
            ads_manager_administrator.prefecture.numero: {
                "ads_count": ads_manager_administrator.ads_count,
                "expected_ads_count": ads_manager_administrator.expected_ads_count,
            }
            for ads_manager_administrator in query_stats.all()
        }

        departements_shpfile = (
            importlib.resources.files("mesads.api.resources")
            / "departements-20140306-100m-shp.zip"
        )
        with shapefile.Reader(departements_shpfile, encoding="latin1") as shp:
            geojson = shp.__geo_interface__
            for feature in geojson["features"]:
                insee_code = feature["properties"]["code_insee"]
                feature["properties"]["ads_count"] = stats[insee_code]["ads_count"]
                feature["properties"]["expected_ads_count"] = stats[insee_code][
                    "expected_ads_count"
                ]

            return Response(geojson)
