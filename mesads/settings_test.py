"""Test settings.

Make sure to reset production data that might have been retrieved from the
environment. We do not want to store files in S3 or send emails in tests.
"""

from .settings import *  # noqa


INSEE_TOKEN = None

EMAIL_HOST = None
EMAIL_PORT = None
EMAIL_HOST_USER = None
EMAIL_HOST_PASSWORD = None
EMAIL_USE_TLS = None

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
