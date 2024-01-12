import csv
import sys

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db.models import Count

from mesads.app.models import ADSManagerRequest
from mesads.fradm.models import Commune


class Command(BaseCommand):
    help = "Returns the mails of all users with a valid request for an ADSManager without ADS registered."

    def handle(self, *args, **options):
        writer = csv.writer(sys.stdout)
        query = (
            ADSManagerRequest.objects.filter(
                accepted=True, ads_manager__no_ads_declared=False
            )
            .annotate(ads_count=Count("ads_manager__ads"))
            .filter(ads_count=0)
        )
        ct = ContentType.objects.get_for_model(Commune)
        for row in query:
            if row.ads_manager.content_type == ct:
                writer.writerow([row.user.email, row.ads_manager.content_object])
