import factory
import pyotp

from ..models import NoteUtilisateur, User, UserAuditEntry


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")

    @factory.post_generation
    def double_auth(self, create, extracted, **kwargs):
        if not extracted:
            return

        self.otp_secret = pyotp.random_base32()

        if create:
            self.save()

    class Params:
        superuser = factory.Trait(
            is_superuser=True,
            is_staff=True,
        )


class UserAuditEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserAuditEntry


class NoteUtilisateurFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NoteUtilisateur
