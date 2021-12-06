from django.urls import include, path

from django_registration.backends.activation.views import RegistrationView

from .forms import CustomUserForm


urlpatterns = [
    path('register/',
        RegistrationView.as_view(
            form_class=CustomUserForm
        ),
        name='django_registration_register',
    ),
    path('', include('django_registration.backends.activation.urls')),
]
