import functools

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
        call_command("import_last_update_file_from_paris")
