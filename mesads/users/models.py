from django.apps import apps
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, UserManager
from django.core.mail import send_mail
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class EmailUserManager(UserManager):
    """Custom manager for users, similar to UserManager, but using email only
    for authentication."""

    def _create_user(self, username, email, password, **extra_fields):
        """This method is a *copy* of django.contrib.auth.model:UserManager,
        except we only use email for authentication.

        I don't know why

            GlobalUserModel = apps.get_model(self.model._meta.app_label, self.model._meta.object_name)

        has to be called, but I do not want to override more than what is just
        necessary.
        """
        email = self.normalize_email(email)
        # Lookup the real model class from the global app registry so this
        # manager method can be used in migrations. This is fine because
        # managers are by definition working on the real model.
        GlobalUserModel = apps.get_model(
            self.model._meta.app_label, self.model._meta.object_name
        )  # noqa
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

    email = models.EmailField(
        _("email address"),
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

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="unique_ci_email",
                violation_error_message="Un utilisateur avec cet email existe déjà.",
            )
        ]

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
