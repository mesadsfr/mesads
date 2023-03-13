from datetime import date

from django.core.management.base import BaseCommand

from mesads.app.models import ADS


class Command(BaseCommand):
    def handle(self, *args, **options):
        for ads in ADS.objects.select_related('ads_manager').prefetch_related('adsuser_set').filter(ads_creation_date__gte=date(2014, 10, 1)):
            if ads.ads_manager.is_locked:

                if (
                    (ads.attribution_date and ads.attribution_date != ads.ads_creation_date)
                    or ads.attribution_reason
                    or ads.attribution_type
                    or ads.transaction_identifier
                ):
                    print(f'Oops, unable to ADS {ads.id} created on {ads.ads_creation_date} which belongs to a locked ADSManager.')
                    for field, value in (
                        ('attribution_date', ads.attribution_date if ads.attribution_date != ads.ads_creation_date else None),
                        ('attribtution_reason', ads.attribution_reason),
                        ('attribution_type', ads.attribution_type),
                        ('transaction_identifier', ads.transaction_identifier)
                    ):
                        if value:
                            print(f'\t{field}: {value}')
                continue

            # For all new ADS, attribution fields should be empty.
            ads.attribution_date = None
            ads.attribution_type = ''
            ads.attribution_reason = ''
            ads.transaction_identifier = ''
            ads.save()

            for ads_user in ads.adsuser_set.all():
                ads_user.delete()
