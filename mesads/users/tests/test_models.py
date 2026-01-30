import datetime

import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from ..models import User
from .factories import NoteUtilisateurFactory, UserAuditEntryFactory

pytestmark = pytest.mark.django_db


def test_show_notation_without_connexion(user: User):
    assert not user.show_notation()


def test_show_notation_with_one_connexion(user: User):
    UserAuditEntryFactory(
        user=user,
        action="login",
    )
    assert not user.show_notation()


def test_show_notation_with_more_than_one_connexion(user: User):
    UserAuditEntryFactory(
        user=user,
        action="login",
    )
    UserAuditEntryFactory(
        user=user,
        action="login",
    )
    assert user.show_notation()


def test_show_notation_with_last_affichage_older_than_a_month(user: User):
    last_affichage = timezone.now() - relativedelta(months=2)
    UserAuditEntryFactory(
        user=user,
        action="login",
    )
    UserAuditEntryFactory(
        user=user,
        action="login",
    )
    NoteUtilisateurFactory(user=user, dernier_affichage=last_affichage.date())
    assert user.show_notation()


def test_show_notation_with_last_affichage_younger_than_a_month(user: User):
    last_affichage = timezone.now() - datetime.timedelta(days=10)
    UserAuditEntryFactory(
        user=user,
        action="login",
    )
    UserAuditEntryFactory(
        user=user,
        action="login",
    )
    NoteUtilisateurFactory(user=user, dernier_affichage=last_affichage.date())
    assert not user.show_notation()


def test_show_notation_with_last_older_than_a_month_and_note_younger_than_six(
    user: User,
):
    last_affichage = timezone.now() - relativedelta(months=2)
    last_note = timezone.now() - relativedelta(months=2)
    UserAuditEntryFactory(
        user=user,
        action="login",
    )
    UserAuditEntryFactory(
        user=user,
        action="login",
    )
    NoteUtilisateurFactory(
        user=user,
        dernier_affichage=last_affichage.date(),
        derniere_note=last_note.date(),
    )
    assert not user.show_notation()


def test_show_notation_with_last_older_than_a_month_and_note_older_than_six(user: User):
    last_affichage = timezone.now() - relativedelta(months=2)
    last_note = timezone.now() - relativedelta(months=7)
    UserAuditEntryFactory(
        user=user,
        action="login",
    )
    UserAuditEntryFactory(
        user=user,
        action="login",
    )
    NoteUtilisateurFactory(
        user=user,
        dernier_affichage=last_affichage.date(),
        derniere_note=last_note.date(),
    )
    assert user.show_notation()


def test_show_notation_with_last_younger_than_a_month_and_note_older_than_six(
    user: User,
):
    last_affichage = timezone.now() - datetime.timedelta(days=10)
    last_note = timezone.now() - relativedelta(months=7)
    UserAuditEntryFactory(
        user=user,
        action="login",
    )
    UserAuditEntryFactory(
        user=user,
        action="login",
    )
    NoteUtilisateurFactory(
        user=user,
        dernier_affichage=last_affichage.date(),
        derniere_note=last_note.date(),
    )
    assert not user.show_notation()
