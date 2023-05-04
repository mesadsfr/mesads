from django.core import mail
from django.conf import settings

from .unittest import ClientTestCase


class TestPasswordResetView(ClientTestCase):
    """Make sure password reset sends HTML email and the contact address is
    present in the email."""

    def test_reset_password(self):
        resp = self.auth_client.post(
            "/auth/password_reset/", {"email": self.auth_user.email}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(settings.MESADS_CONTACT_EMAIL, mail.outbox[0].body)

        self.assertEqual(len(mail.outbox[0].alternatives), 1)
        self.assertEqual(mail.outbox[0].alternatives[0][1], "text/html")
        self.assertIn(settings.MESADS_CONTACT_EMAIL, mail.outbox[0].alternatives[0][0])

    def test_reset_password_invalid_email(self):
        resp = self.auth_client.post(
            "/auth/password_reset/", {"email": "invalidemail@gmail.com"}
        )

        self.assertEqual(resp.status_code, 200)
        self.assertIn("invalide", resp.content.decode("utf8"))
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_password_inactive_account(self):
        user = self.create_user()

        user.obj.is_active = False
        user.obj.save()

        resp = self.auth_client.post(
           "/auth/password_reset/", {"email": user.obj.email}
        )

        self.assertEqual(resp.status_code, 200)
        self.assertIn("Votre compte est inactif", resp.content.decode("utf8"))
        self.assertEqual(len(mail.outbox), 0)


class TestCustomRegistrationView(ClientTestCase):
    def test_send_activation_email(self):
        resp = self.anonymous_client.post(
            "/auth/register/",
            {
                "email": "sdiofnaisodfnqowifqepsio@bla.com",
                "password1": "abcdef123__",
                "password2": "abcdef123__",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(settings.MESADS_CONTACT_EMAIL, mail.outbox[0].body)

        self.assertEqual(len(mail.outbox[0].alternatives), 1)
        self.assertEqual(mail.outbox[0].alternatives[0][1], "text/html")
        self.assertIn(settings.MESADS_CONTACT_EMAIL, mail.outbox[0].alternatives[0][0])
