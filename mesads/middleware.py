from django.shortcuts import redirect
from django.urls import resolve
from django.urls.exceptions import Resolver404


class BackwardCompatibilityURLMiddleware:
    """In the past, all the URLs of the app were in the root of the website and
    only the ADS register existed. Now, the ADS register is in /registre_ads and
    the other URLs are in /other subpaths. This middleware redirects the old
    URLs to the new ones for backward compatibility.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code == 404:
            url = f"/registre_ads{request.path}"
            try:
                resolve(url)
            except Resolver404:
                return response
            return redirect(url, permanent=True)
        return response
