from django import forms
from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm
from django.core.exceptions import ValidationError

from django_registration.forms import RegistrationForm
from django.contrib.auth.forms import AuthenticationForm

from .models import User


class CustomUserForm(RegistrationForm):
    class Meta(RegistrationForm.Meta):
        model = User


class PasswordResetStrictForm(PasswordResetForm):
    def clean_email(self):
        email = self.cleaned_data["email"]

        user = User.objects.filter(email=email).first()

        if not user:
            raise ValidationError(
                "L'email est invalide. Aucun compte n'existe avec cet email."
            )
        if not user.is_active:
            raise ValidationError(
                "Votre compte est inactif, car vous n'avez pas cliqué sur le "
                "lien de confirmation dans l'email que nous vous avons envoyé. Si "
                "vous n'avez pas reçu cet email, veuillez vérifier votre dossier "
                "de courrier indésirable. Si vous ne le trouvez pas, veuillez "
                f"nous contacter à l'adresse {settings.MESADS_CONTACT_EMAIL}"
            )

        return email


class OTPAuthenticationForm(AuthenticationForm):
    otp = forms.CharField(
        required=False,
        label="Vérification",
        help_text="Veuillez entrer le mot de passe à usage unique envoyé sur votre adresse e-mail.",
    )
