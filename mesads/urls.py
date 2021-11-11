from django.contrib import admin
from django.urls import include, path

import debug_toolbar


urlpatterns = [
    path('auth/', include('django.contrib.auth.urls')),
    path('admin/', admin.site.urls),
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    path('', include('mesads.app.urls')),

    path('__debug__/', include(debug_toolbar.urls)),
]
