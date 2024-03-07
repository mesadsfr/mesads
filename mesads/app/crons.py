import functools
from datetime import date

from sentry_sdk import capture_exception

from django.core.management import call_command

from django_cron import CronJobBase, Schedule

from mesads.app.models import ADS


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


class DetectDataInconsistencies(CronJobBase):
    # Run every day
    schedule = Schedule(run_every_mins=60 * 24)

    code = "detect_data_inconsistencies"  # unique code to represent this cron job

    @sentry_exceptions
    def do(self):
        new_ads_with_ads_users = ADS.objects.filter(
            ads_creation_date__isnull=False,
            ads_creation_date__gte=date(2014, 10, 1),
        ).filter(adsuser__isnull=False)
        count = new_ads_with_ads_users.count()
        if count > 0:
            ads_list = ", ".join([str(ads.id) for ads in new_ads_with_ads_users])
            raise ValueError(
                f"Fount data inconsistencies: {count} new ADS, created after October 2014, are linked to an ADSUser (ADS ids: {ads_list}). It should never be the case."
            )
