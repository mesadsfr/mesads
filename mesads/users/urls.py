from django.urls import include, path

from .views import CustomRegistrationView


urlpatterns = [
    path('register/', CustomRegistrationView.as_view(), name='django_registration_register'),
    path('', include('django_registration.backends.activation.urls')),
    path('', include('django.contrib.auth.urls')),
]
