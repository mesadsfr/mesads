from datetime import date

from django.core.management.base import BaseCommand

from mesads.app.models import ADS


class Command(BaseCommand):
    def handle(self, *args, **options):
        for ads in ADS.objects.select_related('ads_manager').prefetch_related('adsuser_set').filter(ads_creation_date__gte=date(2014, 10, 1)):
            if ads.ads_manager.is_locked:
                print(f'Oops, problem with ADS {ads.id} which belongs to a locked ADSManager.')
                continue

            # For all new ADS, attribution fields should be empty.
            ads.attribution_date = None
            ads.attribution_type = ''
            ads.attribution_reason = ''
            ads.transaction_identifier = ''
            ads.save()

            for ads_user in ads.adsuser_set.all():
                ads_user.delete()
