from django.urls import include, path
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register(r"ads-updates", views.ADSUpdatesViewSet, basename="ads-updates")

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path("", include(router.urls)),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path(
        "stats/geojson/per-prefecture/",
        views.StatsGeoJSONPerPrefecture.as_view(),
        name="api.stats.geojson.per-prefecture",
    ),
]
