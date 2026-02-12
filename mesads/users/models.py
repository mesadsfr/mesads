from dateutil.relativedelta import relativedelta
from django.contrib.auth.models import (
    AbstractUser,
    UserManager,
)
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class EmailUserManager(UserManager):
    """Custom manager for users, similar to UserManager, but using email only
    for authentication."""

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("L'adresse email doit être renseignée")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields["is_staff"] is not True:
            raise ValueError("Le superuser doit avoir is_staff=True")
        if extra_fields["is_superuser"] is not True:
            raise ValueError("Le superuser doit avoir is_superuser=True")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """This model is a copy of django.contrib.auth.models.AbstractUser, except
    username is removed, email is unique and we set the custom manager to
    EmailUserManager.

    The goal is to remain compatible with django admin, but have email
    authentication instead of username authentication.
    """

    username = None
    email = models.EmailField(
        _("email address"),
        db_collation="case_insensitive",
        unique=True,
        error_messages={
            "unique": "Un utilisateur avec cet email existe déjà.",
        },
    )

    otp_secret = models.CharField(
        blank=True,
        null=False,
        max_length=64,
    )

    proconnect_sub = models.UUIDField(
        "Identifiant unique proconnect", null=True, blank=True
    )
    proconnect_uid = models.CharField("ID chez le FI", default="", blank=True)
    proconnect_idp_id = models.UUIDField("Identifiant du FI", null=True, blank=True)
    proconnect_siret = models.CharField(
        "SIRET",
        default="",
        blank=True,
    )
    proconnect_chorusdt = models.CharField(
        "Entité ministérielle / Matricule Agent",
        default="",
        blank=True,
    )

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = EmailUserManager()

    def show_notation(self) -> bool:
        note_utilisateur = NoteUtilisateur.objects.filter(user=self).first()
        today = timezone.now().date()
        one_month_ago = today - relativedelta(months=1)
        six_months_ago = today - relativedelta(months=6)
        if note_utilisateur:
            if note_utilisateur.derniere_note is None:
                if note_utilisateur.dernier_affichage is None:
                    return True
                else:
                    return note_utilisateur.dernier_affichage < one_month_ago
            else:
                if note_utilisateur.derniere_note < six_months_ago:
                    return note_utilisateur.dernier_affichage < one_month_ago
                else:
                    return False

        else:
            if UserAuditEntry.objects.filter(user=self, action="login").count() > 1:
                return True
            else:
                return False


class UserAuditEntry(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, null=False)
    action = models.CharField(max_length=64, null=False, blank=False)
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, related_name="audit_entries", null=True
    )
    ip = models.GenericIPAddressField(null=True)
    body = models.TextField(null=False, blank=True)

    class Meta:
        verbose_name = "Historique des connexions"
        verbose_name_plural = "Historiques des connexions"


class NoteUtilisateur(models.Model):
    MINIMUM_NOTE = 1
    MAXIMUM_NOTE = 5

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="note")
    dernier_affichage = models.DateField(
        verbose_name="Date du dernier affichage du composant de notation", null=True
    )
    derniere_note = models.DateField(
        verbose_name="Date de la dernière notation", null=True
    )

    note_facilite = models.PositiveSmallIntegerField(
        verbose_name="Note de facilité d'usage (sur 5)",
        null=True,
        validators=[MaxValueValidator(MINIMUM_NOTE), MinValueValidator(MAXIMUM_NOTE)],
    )

    note_qualite = models.PositiveSmallIntegerField(
        verbose_name="Note de qualité de service (sur 5)",
        null=True,
        validators=[MaxValueValidator(MINIMUM_NOTE), MinValueValidator(MAXIMUM_NOTE)],
    )

    class Meta:
        verbose_name = "Note de l'utilisateur"
        verbose_name_plural = "Notes des utilisateurs"


def get_client_ip(request):
    """In production, REMOTE_ADDR is the load balancer IP, not the client IP. On
    Clever-Cloud, the client IP is in the X-Forwarded-For header."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        # In case of multiple IPs, take the first one
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


@receiver(user_logged_in)
def user_logged_in_callback(sender, request, user, **kwargs):
    UserAuditEntry.objects.create(user=user, action="login", ip=get_client_ip(request))


@receiver(user_logged_out)
def user_logged_out_callback(sender, request, user, **kwargs):
    UserAuditEntry.objects.create(user=user, action="logout", ip=get_client_ip(request))


@receiver(user_login_failed)
def user_login_failed_callback(sender, credentials, request, **kwargs):
    try:
        user = User.objects.get(email=credentials.get("username"))
    except User.DoesNotExist:
        user = None

    UserAuditEntry.objects.create(
        user=user, action="login_failed", ip=get_client_ip(request), body=credentials
    )
