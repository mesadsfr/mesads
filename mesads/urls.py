from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from .app import views
from .admin_views import StatistiquesView

import debug_toolbar


urlpatterns = [
    path("api/", include("mesads.api.urls")),
    path("auth/", include("mesads.users.urls")),
    path("fradm/", include("mesads.fradm.urls")),
    path(
        "admin/statistiques/",
        admin.site.admin_view(StatistiquesView.as_view()),
        name="admin-statistiques",
    ),
    path("admin/", admin.site.urls),
    path("", include("mesads.app.urls")),
    path("relais/", include("mesads.vehicules_relais.urls")),
    path("__debug__/", include(debug_toolbar.urls)),
    path("markdownx/", include("markdownx.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


handler500 = lambda request: views.HTTP500View.as_view()(request)  # noqa
