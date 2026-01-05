import datetime

from dateutil.relativedelta import relativedelta
from django.test import TestCase
from django.utils import timezone

from .factories import NoteUtilisateurFactory, UserAuditEntryFactory, UserFactory


class TestMethodShowNotation(TestCase):
    def setUp(self):
        super().setUp()
        self.user = UserFactory()

    def test_show_notation_without_connexion(self):
        self.assertFalse(self.user.show_notation())

    def test_show_notation_with_one_connexion(self):
        UserAuditEntryFactory(
            user=self.user,
            action="login",
        )
        self.assertFalse(self.user.show_notation())

    def test_show_notation_with_more_than_one_connexion(self):
        UserAuditEntryFactory(
            user=self.user,
            action="login",
        )
        UserAuditEntryFactory(
            user=self.user,
            action="login",
        )
        self.assertTrue(self.user.show_notation())

    def test_show_notation_with_last_affichage_older_than_a_month(self):
        last_affichage = timezone.now() - relativedelta(months=2)
        UserAuditEntryFactory(
            user=self.user,
            action="login",
        )
        UserAuditEntryFactory(
            user=self.user,
            action="login",
        )
        NoteUtilisateurFactory(user=self.user, dernier_affichage=last_affichage.date())
        self.assertTrue(self.user.show_notation())

    def test_show_notation_with_last_affichage_younger_than_a_month(self):
        last_affichage = timezone.now() - datetime.timedelta(days=10)
        UserAuditEntryFactory(
            user=self.user,
            action="login",
        )
        UserAuditEntryFactory(
            user=self.user,
            action="login",
        )
        NoteUtilisateurFactory(user=self.user, dernier_affichage=last_affichage.date())
        self.assertFalse(self.user.show_notation())

    def test_show_notation_with_last_older_than_a_month_and_note_younger_than_six(self):
        last_affichage = timezone.now() - relativedelta(months=2)
        last_note = timezone.now() - relativedelta(months=2)
        UserAuditEntryFactory(
            user=self.user,
            action="login",
        )
        UserAuditEntryFactory(
            user=self.user,
            action="login",
        )
        NoteUtilisateurFactory(
            user=self.user,
            dernier_affichage=last_affichage.date(),
            derniere_note=last_note.date(),
        )
        self.assertFalse(self.user.show_notation())

    def test_show_notation_with_last_older_than_a_month_and_note_older_than_six(self):
        last_affichage = timezone.now() - relativedelta(months=2)
        last_note = timezone.now() - relativedelta(months=7)
        UserAuditEntryFactory(
            user=self.user,
            action="login",
        )
        UserAuditEntryFactory(
            user=self.user,
            action="login",
        )
        NoteUtilisateurFactory(
            user=self.user,
            dernier_affichage=last_affichage.date(),
            derniere_note=last_note.date(),
        )
        self.assertTrue(self.user.show_notation())

    def test_show_notation_with_last_younger_than_a_month_and_note_older_than_six(self):
        last_affichage = timezone.now() - datetime.timedelta(days=10)
        last_note = timezone.now() - relativedelta(months=7)
        UserAuditEntryFactory(
            user=self.user,
            action="login",
        )
        UserAuditEntryFactory(
            user=self.user,
            action="login",
        )
        NoteUtilisateurFactory(
            user=self.user,
            dernier_affichage=last_affichage.date(),
            derniere_note=last_note.date(),
        )
        self.assertFalse(self.user.show_notation())
