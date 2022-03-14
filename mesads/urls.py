from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from .app import views

import debug_toolbar


urlpatterns = [
    path('auth/', include('mesads.users.urls')),
    path('fradm/', include('mesads.fradm.urls')),
    path('admin/', admin.site.urls),
    path('', include('mesads.app.urls')),

    path('__debug__/', include(debug_toolbar.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


handler500 = lambda request: views.HTTP500View.as_view()(request)  # noqa
