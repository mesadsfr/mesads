from django.core.management.base import BaseCommand
from django.db import transaction

from mesads.app.models import ADS, ADSUser


class Command(BaseCommand):
    help = 'Temporary command to strip CharFields from databsae'

    def handle(self, *args, **options):
        with transaction.atomic():
            for ads in ADS.objects.select_related('ads_manager').all():
                if not ads.ads_manager.is_locked:
                    ads.clean()
                    ads.save()

            for ads_user in ADSUser.objects.all():
                ads_user.clean()
                ads_user.save()
