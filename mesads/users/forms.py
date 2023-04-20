from django.contrib.auth.forms import PasswordResetForm
from django.core.exceptions import ValidationError

from django_registration.forms import RegistrationForm

from .models import User


class CustomUserForm(RegistrationForm):
    class Meta(RegistrationForm.Meta):
        model = User


class PasswordResetStrictForm(PasswordResetForm):
    def clean_email(self):
        email = self.cleaned_data["email"]

        if not User.objects.filter(email=email).count():
            raise ValidationError(
                "L'email est invalide. Aucun compte n'existe avec cet email."
            )

        return email
