import http
from dateutil.relativedelta import relativedelta
from django.urls import reverse
from django.utils import timezone

from mesads.users.models import NoteUtilisateur
from mesads.unittest import ClientTestCase


class TestNotationView(ClientTestCase):
    def test_post_close_without_existing_note(self):
        client_connecte, user = self.create_client()
        self.assertEqual(NoteUtilisateur.objects.filter(user=user).count(), 0)
        response = client_connecte.post(
            reverse("app.note-service"), {"action": "close"}
        )

        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertEqual(NoteUtilisateur.objects.filter(user=user).count(), 1)
        note = NoteUtilisateur.objects.filter(user=user).first()
        self.assertEqual(note.dernier_affichage, timezone.now().date())
        self.assertIsNone(note.derniere_note)
        self.assertIsNone(note.note_facilite)
        self.assertIsNone(note.note_qualite)

    def test_post_note_without_existing_note(self):
        client_connecte, user = self.create_client()
        self.assertEqual(NoteUtilisateur.objects.filter(user=user).count(), 0)
        response = client_connecte.post(
            reverse("app.note-service"),
            {
                "action": "note",
                "note_facilite": "4",
                "note_qualite": "5",
            },
        )

        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertEqual(NoteUtilisateur.objects.filter(user=user).count(), 1)
        note = NoteUtilisateur.objects.filter(user=user).first()
        self.assertEqual(note.dernier_affichage, timezone.now().date())
        self.assertEqual(note.derniere_note, timezone.now().date())
        self.assertEqual(note.note_qualite, 5)
        self.assertEqual(note.note_facilite, 4)

    def test_post_close_with_existing_note(self):
        client_connecte, user = self.create_client()
        initial_date = timezone.now().date() - relativedelta(months=1)
        note = NoteUtilisateur.objects.create(
            user=user,
            dernier_affichage=initial_date,
            derniere_note=initial_date,
            note_facilite=3,
            note_qualite=3,
        )
        self.assertEqual(NoteUtilisateur.objects.filter(user=user).count(), 1)
        response = client_connecte.post(
            reverse("app.note-service"), {"action": "close"}
        )

        self.assertEqual(response.status_code, http.HTTPStatus.OK)

        self.assertEqual(NoteUtilisateur.objects.filter(user=user).count(), 1)
        note.refresh_from_db()
        self.assertEqual(note.dernier_affichage, timezone.now().date())
        self.assertEqual(note.derniere_note, initial_date)
        self.assertEqual(note.note_facilite, 3)
        self.assertEqual(note.note_qualite, 3)

    def test_post_note_with_existing_note(self):
        client_connecte, user = self.create_client()
        initial_date = timezone.now().date() - relativedelta(months=1)
        note = NoteUtilisateur.objects.create(
            user=user,
            dernier_affichage=initial_date,
            derniere_note=initial_date,
            note_facilite=3,
            note_qualite=3,
        )
        self.assertEqual(NoteUtilisateur.objects.filter(user=user).count(), 1)
        response = client_connecte.post(
            reverse("app.note-service"),
            {
                "action": "note",
                "note_facilite": 4,
                "note_qualite": 5,
            },
        )

        self.assertEqual(response.status_code, http.HTTPStatus.OK)

        self.assertEqual(NoteUtilisateur.objects.filter(user=user).count(), 1)
        note.refresh_from_db()
        self.assertEqual(note.dernier_affichage, timezone.now().date())
        self.assertEqual(note.derniere_note, timezone.now().date())
        self.assertEqual(note.note_facilite, 4)
        self.assertEqual(note.note_qualite, 5)
