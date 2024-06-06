from django.contrib import messages
from django.core import mail

from mesads.fradm.models import EPCI, Prefecture

from ..models import (
    ADSManager,
    ADSManagerRequest,
    Notification,
)
from ..unittest import ClientTestCase


class TestADSManagerAdminView(ClientTestCase):
    def setUp(self):
        super().setUp()
        self.ads_manager_request = ADSManagerRequest.objects.create(
            user=self.create_user().obj,
            ads_manager=self.ads_manager_city35,
            accepted=None,
        )

    def test_permissions(self):
        for client_name, client, expected_status in (
            ("admin", self.admin_client, 200),
            ("anonymous", self.anonymous_client, 302),
            ("auth", self.auth_client, 404),
            ("ads_manager 35", self.ads_manager_city35_client, 404),
            ("ads_manager_admin 35", self.ads_manager_administrator_35_client, 200),
        ):
            with self.subTest(client_name=client_name, expected_status=expected_status):
                resp = client.get("/registre_ads/admin_gestion")
                self.assertEqual(resp.status_code, expected_status)

    def test_invalid_action(self):
        resp = self.ads_manager_administrator_35_client.post(
            "/registre_ads/admin_gestion", {"action": "xxx", "request_id": 1}
        )
        self.assertEqual(resp.status_code, 400)

    def test_invalid_request_id(self):
        resp = self.ads_manager_administrator_35_client.post(
            "/registre_ads/admin_gestion", {"action": "accept", "request_id": 12342}
        )
        self.assertEqual(resp.status_code, 404)

    def test_accept(self):
        self.assertEqual(len(mail.outbox), 0)

        resp = self.ads_manager_administrator_35_client.post(
            "/registre_ads/admin_gestion",
            {"action": "accept", "request_id": self.ads_manager_request.id},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/registre_ads/admin_gestion")
        self.ads_manager_request.refresh_from_db()
        self.assertTrue(self.ads_manager_request.accepted)
        self.assertEqual(len(mail.outbox), 1)

    def test_deny(self):
        self.assertEqual(len(mail.outbox), 0)

        resp = self.ads_manager_administrator_35_client.post(
            "/registre_ads/admin_gestion",
            {"action": "deny", "request_id": self.ads_manager_request.id},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/registre_ads/admin_gestion")
        self.ads_manager_request.refresh_from_db()
        self.assertFalse(self.ads_manager_request.accepted)
        self.assertEqual(len(mail.outbox), 1)

    def test_sort(self):
        for ads_manager in ADSManager.objects.all():
            ADSManagerRequest.objects.create(
                user=self.create_user().obj,
                ads_manager=ads_manager,
                accepted=None,
            )
            resp = self.ads_manager_administrator_35_client.get(
                "/registre_ads/admin_gestion",
            )
            self.assertEqual(resp.status_code, 200)

            resp = self.ads_manager_administrator_35_client.get(
                "/registre_ads/admin_gestion?sort=name",
            )
            self.assertEqual(resp.status_code, 200)


class TestADSManagerRequestView(ClientTestCase):
    def setUp(self):
        super().setUp()
        self.initial_ads_managers_count = ADSManagerRequest.objects.count()

    def test_permissions(self):
        for client_name, client, expected_status in (
            ("anonymous", self.anonymous_client, 302),
            ("auth", self.auth_client, 200),
            ("ads_manager 35", self.ads_manager_city35_client, 200),
            ("ads_manager_admin 35", self.ads_manager_administrator_35_client, 200),
        ):
            with self.subTest(client_name=client_name, expected_status=expected_status):
                resp = client.get("/registre_ads/gestion")
                self.assertEqual(resp.status_code, expected_status)

    def test_create_request_invalid_id(self):
        """Provide the id of a non-existing object."""
        resp = self.auth_client.post("/registre_ads/gestion", {"commune": 9999})
        self.assertEqual(len(resp.context["form"].errors["__all__"]), 1)

    def test_create_request_commune(self):
        resp = self.auth_client.post(
            "/registre_ads/gestion", {"commune": self.commune_melesse.id}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            ADSManagerRequest.objects.count(), self.initial_ads_managers_count + 1
        )

        # Make sure django message is in the next request
        resp = self.auth_client.get("/registre_ads/gestion")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["messages"]), 1)
        self.assertEqual(list(resp.context["messages"])[0].level, messages.SUCCESS)

        # If there is a ADSManagerAdministrator related to the commune, an email is sent for each member.
        # The base class ClientTestCase configures Melesse to be managed by the ADSManagerAdministrator entry of
        # l'Ille-et-Vilaine.
        self.assertEqual(len(mail.outbox), 1)

        #
        # If we send the same request, a warning message is displayed and no email is sent.
        #
        resp = self.auth_client.post(
            "/registre_ads/gestion", {"commune": self.commune_melesse.id}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            ADSManagerRequest.objects.count(), self.initial_ads_managers_count + 1
        )

        # Check warning message
        resp = self.auth_client.get("/registre_ads/gestion")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["messages"]), 1)
        self.assertEqual(list(resp.context["messages"])[0].level, messages.WARNING)
        # No new email
        self.assertEqual(len(mail.outbox), 1)

    def test_create_commune_notification_false(self):
        """The ADSManagerAdministrator of self.commune_melesse is linked to the
        user ads_manager_administrator_35_user, which has a Notification object
        set to False: no email should be sent when a request is made."""
        Notification.objects.create(
            user=self.ads_manager_administrator_35_user,
            ads_manager_requests=False,
        )
        self.auth_client.post(
            "/registre_ads/gestion", {"commune": self.commune_melesse.id}
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_create_commune_notification_true(self):
        """The ADSManagerAdministrator of self.commune_melesse is linked to the
        user ads_manager_administrator_35_user, which has a Notification object
        set to False: an email should be sent when a request is made."""
        Notification.objects.create(
            user=self.ads_manager_administrator_35_user,
            ads_manager_requests=True,
        )
        self.auth_client.post(
            "/registre_ads/gestion", {"commune": self.commune_melesse.id}
        )
        self.assertEqual(len(mail.outbox), 1)

    def test_create_commune_notification_empty(self):
        """The ADSManagerAdministrator of self.commune_melesse is linked to the
        user ads_manager_administrator_35_user, but no Notification is linked to the user. By default, we should send an email.
        """
        self.auth_client.post(
            "/registre_ads/gestion", {"commune": self.commune_melesse.id}
        )
        self.assertEqual(len(mail.outbox), 1)

    def test_create_request_epci(self):
        epci = EPCI.objects.first()
        resp = self.auth_client.post("/registre_ads/gestion", {"epci": epci.id})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            ADSManagerRequest.objects.count(), self.initial_ads_managers_count + 1
        )

        # Make sure django message is in the next request
        resp = self.auth_client.get("/registre_ads/gestion")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["messages"]), 1)
        self.assertEqual(list(resp.context["messages"])[0].level, messages.SUCCESS)

        #
        # If we send the same request, no object is created and a warning message is displayed.
        #
        resp = self.auth_client.post("/registre_ads/gestion", {"epci": epci.id})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            ADSManagerRequest.objects.count(), self.initial_ads_managers_count + 1
        )

        resp = self.auth_client.get("/registre_ads/gestion")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["messages"]), 1)
        self.assertEqual(list(resp.context["messages"])[0].level, messages.WARNING)

    def test_create_request_prefecture(self):
        prefecture = Prefecture.objects.first()
        resp = self.auth_client.post(
            "/registre_ads/gestion", {"prefecture": prefecture.id}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            ADSManagerRequest.objects.count(), self.initial_ads_managers_count + 1
        )

        # Make sure django message is in the next request
        resp = self.auth_client.get("/registre_ads/gestion")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["messages"]), 1)
        self.assertEqual(list(resp.context["messages"])[0].level, messages.SUCCESS)

        #
        # If we send the same request, no object is created and a warning message is displayed.
        #
        resp = self.auth_client.post(
            "/registre_ads/gestion", {"prefecture": prefecture.id}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            ADSManagerRequest.objects.count(), self.initial_ads_managers_count + 1
        )

        # Make sure django message is in the next request
        resp = self.auth_client.get("/registre_ads/gestion")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["messages"]), 1)
        self.assertEqual(list(resp.context["messages"])[0].level, messages.WARNING)
