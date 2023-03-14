from datetime import date

from django.db.models import Q
from django.core.management.base import BaseCommand

from mesads.app.models import ADS


class Command(BaseCommand):
    def handle(self, *args, **options):
        # Define used_by_owner for old ADS that don't have this field set.
        for ads in ADS.objects.prefetch_related('adsuser_set').filter(ads_creation_date__lt=date(2014, 10, 1), used_by_owner=None):
            if ads.adsuser_set.count() == 0:
                ads.used_by_owner = True
            else:
                ads.used_by_owner = False
            ads.save()

        for ads in ADS.objects.prefetch_related('adsuser_set').filter(ads_creation_date__gte=date(2014, 10, 1)).filter(~Q(used_by_owner=None)):
            ads.used_by_owner = None
            ads.save()
