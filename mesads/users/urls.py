from django.conf import settings
from django.contrib.auth.views import PasswordResetView
from django.urls import include, path
from django.views.generic import TemplateView

from .forms import PasswordResetStrictForm
from .views import OTPLoginView

urlpatterns = [
    path("", include("django_registration.backends.activation.urls")),
    # Override password_reset to send HTML email
    path(
        "password_reset/",
        PasswordResetView.as_view(
            form_class=PasswordResetStrictForm,
            email_template_name="registration/password_reset_email.txt",
            html_email_template_name="registration/password_reset_email.mjml",
            extra_email_context={"MESADS_CONTACT_EMAIL": settings.MESADS_CONTACT_EMAIL},
        ),
        name="password_reset",
    ),
    path(
        "inscription/",
        TemplateView.as_view(template_name="registration/pre_register.html"),
        name="pre_register",
    ),
    path(
        "login/",
        OTPLoginView.as_view(),
        name="override.login",
    ),
    path("", include("django.contrib.auth.urls")),
]
