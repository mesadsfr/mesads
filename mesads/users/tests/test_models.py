import datetime
from dateutil.relativedelta import relativedelta
from django.test import TestCase
from django.utils import timezone
from mesads.users.models import User, UserAuditEntry, NoteUtilisateur


class TestMethodShowNotation(TestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(email="email@test.com")

    def test_show_notation_without_connexion(self):
        self.assertFalse(self.user.show_notation())

    def test_show_notation_with_one_connexion(self):
        UserAuditEntry.objects.create(
            user=self.user,
            action="login",
        )
        self.assertFalse(self.user.show_notation())

    def test_show_notation_with_more_than_one_connexion(self):
        UserAuditEntry.objects.create(
            user=self.user,
            action="login",
        )
        UserAuditEntry.objects.create(
            user=self.user,
            action="login",
        )
        self.assertTrue(self.user.show_notation())

    def test_show_notation_with_last_affichage_older_than_a_month(self):
        last_affichage = timezone.now() - relativedelta(months=2)
        UserAuditEntry.objects.create(
            user=self.user,
            action="login",
        )
        UserAuditEntry.objects.create(
            user=self.user,
            action="login",
        )
        NoteUtilisateur.objects.create(
            user=self.user, dernier_affichage=last_affichage.date()
        )
        self.assertTrue(self.user.show_notation())

    def test_show_notation_with_last_affichage_younger_than_a_month(self):
        last_affichage = timezone.now() - datetime.timedelta(days=10)
        UserAuditEntry.objects.create(
            user=self.user,
            action="login",
        )
        UserAuditEntry.objects.create(
            user=self.user,
            action="login",
        )
        NoteUtilisateur.objects.create(
            user=self.user, dernier_affichage=last_affichage.date()
        )
        self.assertFalse(self.user.show_notation())

    def test_show_notation_with_last_older_than_a_month_and_note_younger_than_six(self):
        last_affichage = timezone.now() - relativedelta(months=2)
        last_note = timezone.now() - relativedelta(months=2)
        UserAuditEntry.objects.create(
            user=self.user,
            action="login",
        )
        UserAuditEntry.objects.create(
            user=self.user,
            action="login",
        )
        NoteUtilisateur.objects.create(
            user=self.user,
            dernier_affichage=last_affichage.date(),
            derniere_note=last_note.date(),
        )
        self.assertFalse(self.user.show_notation())

    def test_show_notation_with_last_older_than_a_month_and_note_older_than_six(self):
        last_affichage = timezone.now() - relativedelta(months=2)
        last_note = timezone.now() - relativedelta(months=7)
        UserAuditEntry.objects.create(
            user=self.user,
            action="login",
        )
        UserAuditEntry.objects.create(
            user=self.user,
            action="login",
        )
        NoteUtilisateur.objects.create(
            user=self.user,
            dernier_affichage=last_affichage.date(),
            derniere_note=last_note.date(),
        )
        self.assertTrue(self.user.show_notation())

    def test_show_notation_with_last_younger_than_a_month_and_note_older_than_six(self):
        last_affichage = timezone.now() - datetime.timedelta(days=10)
        last_note = timezone.now() - relativedelta(months=7)
        UserAuditEntry.objects.create(
            user=self.user,
            action="login",
        )
        UserAuditEntry.objects.create(
            user=self.user,
            action="login",
        )
        NoteUtilisateur.objects.create(
            user=self.user,
            dernier_affichage=last_affichage.date(),
            derniere_note=last_note.date(),
        )
        self.assertFalse(self.user.show_notation())
