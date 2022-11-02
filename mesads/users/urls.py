from django.contrib.auth.views import LoginView, PasswordResetView
from django.conf import settings
from django.urls import include, path

from .forms import PasswordResetStrictForm
from .views import CustomRegistrationView


urlpatterns = [
    path('register/', CustomRegistrationView.as_view(), name='django_registration_register'),
    path('', include('django_registration.backends.activation.urls')),

    # Override password_reset to send HTML email
    path('password_reset/', PasswordResetView.as_view(
        form_class=PasswordResetStrictForm,
        html_email_template_name='registration/html_password_reset_email.html',
        extra_email_context={'MESADS_CONTACT_EMAIL': settings.MESADS_CONTACT_EMAIL}
    ), name='password_reset'),

    # By default, /auth/login displays the login form to authenticated users,
    # and also a permission error message if ?next is set. Override to force
    # redirect to ?next or to LOGIN_REDIRECT_URL.
    path('login/', LoginView.as_view(redirect_authenticated_user=True)),

    path('', include('django.contrib.auth.urls')),
]
