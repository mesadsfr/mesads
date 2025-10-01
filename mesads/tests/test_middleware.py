from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from ..middleware import BackwardCompatibilityURLMiddleware


class TestBackwardCompatibilityURLMiddleware(TestCase):
    def test_redirection(self):
        factory = RequestFactory()

        # These URLs exist with the prefix /registre_ads
        for url in (
            "/gestion/123/",
            "/gestion/3432/arrete",
        ):
            middleware = BackwardCompatibilityURLMiddleware(
                lambda request: HttpResponse(status=404)
            )
            request = factory.get(url)
            response = middleware(request)
            self.assertEqual(response.status_code, 301)

        # These URLs don't exist
        for url in (
            "/whatever",
            "/xx",
        ):
            middleware = BackwardCompatibilityURLMiddleware(
                lambda request: HttpResponse(status=404)
            )
            request = factory.get(url)
            response = middleware(request)
            self.assertEqual(response.status_code, 404)

        # These URLs exist
        for url in (
            "/admin",
            "/auth/login",
        ):
            middleware = BackwardCompatibilityURLMiddleware(
                lambda request: HttpResponse(status=200)
            )
            request = factory.get(url)
            response = middleware(request)
            self.assertEqual(response.status_code, 200)
