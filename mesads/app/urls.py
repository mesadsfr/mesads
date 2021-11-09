from django.urls import include, path

from .views import HomepageView


urlpatterns = [
    path('', HomepageView.as_view()),
]
