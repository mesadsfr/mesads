from django.test import TestCase


class TestHTMLMetadata(TestCase):
    def test_html_metadata(self):
        response = self.client.get("/auth/login/")
        self.assertEqual(response.status_code, 200)
        self.assertIn('<meta name="description"', response.content.decode("utf8"))

        response = self.client.get("/doesnotexist")
        self.assertEqual(response.status_code, 404)
        self.assertIn("<title>", response.content.decode("utf8"))
        self.assertNotIn('<meta name="description"', response.content.decode("utf8"))
