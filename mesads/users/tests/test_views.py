import re

from django.core import mail
from django.conf import settings

from ..unittest import ClientTestCase


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

        resp = self.auth_client.post("/auth/password_reset/", {"email": user.obj.email})

        self.assertEqual(resp.status_code, 200)
        self.assertIn("Votre compte est inactif", resp.content.decode("utf8"))
        self.assertEqual(len(mail.outbox), 0)


class TestCustomRegistrationView(ClientTestCase):
    def test_send_activation_email(self):
        resp = self.anonymous_client.post(
            "/auth/register/",
            {
                "email": "sdiofnaisodfnqowifqepsio@bla.com",
                "password1": "aBcdef123__",
                "password2": "aBcdef123__",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(settings.MESADS_CONTACT_EMAIL, mail.outbox[0].body)

        self.assertEqual(len(mail.outbox[0].alternatives), 1)
        self.assertEqual(mail.outbox[0].alternatives[0][1], "text/html")
        self.assertIn(settings.MESADS_CONTACT_EMAIL, mail.outbox[0].alternatives[0][0])


class Test2FALoginView(ClientTestCase):
    def test_2fa_login(self):
        user = self.create_user(double_auth=True)

        # Send login/password without OTP and verify that the OTP is sent by email
        resp = self.anonymous_client.post(
            "/auth/login/",
            {
                "username": user.obj.email,
                "password": user.clear_password,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("mot de passe à usage unique", resp.content.decode("utf8"))

        self.assertEqual(len(mail.outbox[0].alternatives), 1)
        self.assertEqual(mail.outbox[0].alternatives[0][1], "text/html")

        matches = re.search(r"(\d{6})", mail.outbox[0].body)
        self.assertIsNotNone(matches)

        otp_code = matches.groups(1)[0]

        # Invalid OTP given
        resp = self.anonymous_client.post(
            "/auth/login/",
            {
                "username": user.obj.email,
                "password": user.clear_password,
                "otp": "xxx",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Le code est invalide", resp.content.decode("utf8"))

        # Validate the OTP received by email
        resp = self.anonymous_client.post(
            "/auth/login/",
            {
                "username": user.obj.email,
                "password": user.clear_password,
                "otp": otp_code,
            },
        )
        self.assertEqual(resp.status_code, 302)
