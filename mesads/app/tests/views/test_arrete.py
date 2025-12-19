import http

from django.urls import reverse

from mesads.app.views import TelechargementArreteView
from mesads.unittest import ClientTestCase


class TestArretesListView(ClientTestCase):
    def test_permissions(self):
        for client_name, client, expected_status in (
            ("anonymous", self.anonymous_client, http.HTTPStatus.FOUND),
            ("auth", self.auth_client, http.HTTPStatus.NOT_FOUND),
            ("ads_manager 35", self.ads_manager_city35_client, http.HTTPStatus.OK),
            (
                "ads_manager_administrator 35",
                self.ads_manager_administrator_35_client,
                http.HTTPStatus.OK,
            ),
        ):
            with self.subTest(client_name=client_name, expected_status=expected_status):
                response = client.get(
                    reverse(
                        "app.arretes-list",
                        kwargs={"manager_id": self.ads_manager_city35.id},
                    )
                )
                self.assertEqual(response.status_code, expected_status)
                if expected_status == http.HTTPStatus.OK:
                    self.assertTemplateUsed(
                        response, "pages/ads_register/arretes_liste.html"
                    )


class TestArreteDownloadView(ClientTestCase):
    def test_get_arrete_without_query_param(self):
        response = self.ads_manager_city35_client.get(
            reverse(
                "app.arrete-download", kwargs={"manager_id": self.ads_manager_city35.id}
            )
        )
        self.assertEqual(response.status_code, http.HTTPStatus.NOT_FOUND)

    def test_get_arrete_with_wrong_query_param(self):
        q_params = "?modele_arrete=tralalala"
        base_url = reverse(
            "app.arrete-download", kwargs={"manager_id": self.ads_manager_city35.id}
        )

        response = self.ads_manager_city35_client.get(f"{base_url}{q_params}")
        self.assertEqual(response.status_code, http.HTTPStatus.NOT_FOUND)

    def test_get_arrete_ok(self):
        base_url = reverse(
            "app.arrete-download", kwargs={"manager_id": self.ads_manager_city35.id}
        )
        for modele_arrete, expected_file in (
            (key, value["file_name"])
            for key, value in TelechargementArreteView.modele_arretes.items()
        ):
            with self.subTest(modele_arrete=modele_arrete, expected_file=expected_file):
                q_params = f"?modele_arrete={modele_arrete}"
                response = self.ads_manager_city35_client.get(f"{base_url}{q_params}")
                self.assertEqual(response.status_code, http.HTTPStatus.OK)
                self.assertEqual(response.filename, expected_file)
