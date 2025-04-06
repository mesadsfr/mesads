import functools
import io
from contextlib import redirect_stdout, redirect_stderr


from sentry_sdk import capture_exception

from django.core.management import call_command

from django_cron import CronJobBase, Schedule


def sentry_exceptions(func):
    @functools.wraps(func)
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            capture_exception(e)
            raise

    return inner


class ImportDataForParis(CronJobBase):
    # Run every day
    schedule = Schedule(run_every_mins=60 * 24)

    code = (
        "import_last_update_file_from_Paris"  # unique code to represent this cron job
    )

    @sentry_exceptions
    def do(self):
        # Redirect stdout and stderr to a buffer to capture the output of the
        # command. By returning it, django-cron will log it in the database.
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(buf):
            call_command("import_last_update_file_from_paris")
        return buf.getvalue()


class DeleteOldUsers(CronJobBase):
    # Run every week
    schedule = Schedule(run_every_mins=60 * 24 * 7)

    code = "remove_old_accounts"  # unique code to represent this cron job

    @sentry_exceptions
    def do(self):
        # Redirect stdout and stderr to a buffer to capture the output of the
        # command. By returning it, django-cron will log it in the database.
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(buf):
            call_command("remove_old_accounts")
        return buf.getvalue()
