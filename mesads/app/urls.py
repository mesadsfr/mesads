from django.contrib.auth.decorators import login_required
from django.urls import include, path

from .views import HomepageView


urlpatterns = [
    path('', login_required(HomepageView.as_view())),
]
