from dateutil.relativedelta import relativedelta
from django.apps import apps
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, UserManager
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.core.mail import send_mail
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class EmailUserManager(UserManager):
    """Custom manager for users, similar to UserManager, but using email only
    for authentication."""

    def _create_user(self, username, email, password, **extra_fields):
        """This method is a *copy* of django.contrib.auth.model:UserManager,
        except we only use email for authentication.

        I don't know why

            GlobalUserModel = apps.get_model(
                self.model._meta.app_label, self.model._meta.object_name
            )

        has to be called, but I do not want to override more than what is just
        necessary.
        """
        email = self.normalize_email(email)
        # Lookup the real model class from the global app registry so this
        # manager method can be used in migrations. This is fine because
        # managers are by definition working on the real model.
        apps.get_model(self.model._meta.app_label, self.model._meta.object_name)  # noqa
        user = self.model(email=email, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        return super().create_user(None, email=email, password=password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        return super().create_superuser(
            None, email=email, password=password, **extra_fields
        )


class User(AbstractBaseUser, PermissionsMixin):
    """This model is a copy of django.contrib.auth.models.AbstractUser, except
    username is removed, email is unique and we set the custom manager to
    EmailUserManager.

    The goal is to remain compatible with django admin, but have email
    authentication instead of username authentication.
    """

    email = models.TextField(
        _("email address"),
        db_collation="case_insensitive",
        unique=True,
        error_messages={
            "unique": "Un utilisateur avec cet email existe déjà.",
        },
    )
    objects = EmailUserManager()

    first_name = models.CharField(_("first name"), max_length=150, blank=True)
    last_name = models.CharField(_("last name"), max_length=150, blank=True)
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)

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

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def clean(self):
        ret = super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)
        return ret

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = "%s %s" % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name

    def email_user(self, subject, message, from_email=None, **kwargs):
        """Send an email to this user."""
        send_mail(subject, message, from_email, [self.email], **kwargs)

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
