import unittest

from django.core.management import call_command


class TestMigrationsApplied(unittest.TestCase):

    def test_migrations(self):
        command = ['makemigrations', '--check', '--dry-run']
        import io

        with io.StringIO() as out:
            try:
                call_command(*command, stdout=out)
            except SystemExit:
                self.fail(f"Missing migrations. Run `python manage.py makemigrations` and commit the new migration files.")
