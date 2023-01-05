from django.core.management import call_command

from django_cron import CronJobBase, Schedule


class ImportDataForParis(CronJobBase):
    # Run every day
    schedule = Schedule(run_every_mins=60 * 24)

    code = 'import_last_update_file_from_Paris'  # unique code to represent this cron job

    def do(self):
        call_command('import_last_update_file_from_paris')
