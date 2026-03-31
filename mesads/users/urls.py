from django.urls import path
from django.views.generic import TemplateView

from .views import LoginView

urlpatterns = [
    path(
        "inscription/",
        TemplateView.as_view(template_name="registration/pre_register.html"),
        name="pre_register",
    ),
    path(
        "login/",
        LoginView.as_view(),
        name="override.login",
    ),
]
