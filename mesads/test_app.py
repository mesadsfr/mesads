import io
import unittest

import pytest

from django.conf import settings
from django.core.management import call_command


@pytest.mark.django_db
class TestMigrationsApplied(unittest.TestCase):
    def test_migrations(self):
        """The goal of this unittest is to ensure that all migrations have been applied.

        Unfortunately, a migration file is missing in django_cron (see
        https://github.com/Tivix/django-cron/pull/224) so `makemigrations`
        always generates a migration file for this application.

        To solve this problem, we only check if migrations are missing for our
        applications.
        """
        our_apps = [
            app.split(".")[-1] for app in settings.INSTALLED_APPS if "mesads" in app
        ]

        command = ["makemigrations", "--check", "--dry-run", *our_apps]

        with io.StringIO() as out:
            try:
                call_command(*command, stdout=out)
            except SystemExit:
                out.seek(0)
                self.fail(
                    f"Missing migrations. Run `python manage.py makemigrations` and commit the new migration files. Output was:\n{out.read()}"
                )
