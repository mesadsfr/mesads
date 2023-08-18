from django.core.management.base import BaseCommand
from django.db.models import Count

from mesads.app.models import ADS


class Command(BaseCommand):
    def handle(self, **opts):
        handled = {}
        q = (
            ADS.objects.filter(used_by_owner=True)
            .annotate(count=Count("adsuser"))
            .filter(count__gt=0, adsuser__deleted_at__isnull=True)
        )

        for ads in q:
            done = False
            if ads.id in handled:
                continue

            handled[ads.id] = {
                "ads": ads,
                "emails": [
                    req.user.email
                    for req in ads.ads_manager.adsmanagerrequest_set.all()
                ],
            }

            if ads.owner_siret:
                users = ads.adsuser_set.all()
                if len(users) == 1:
                    if users[0].siret == ads.owner_siret:
                        users[0].delete()
                        done = True
                    else:
                        if (
                            ads.owner_license_number == users[0].license_number
                            or not users[0].license_number
                        ):
                            users[0].license_number = ads.owner_license_number
                            ads.owner_license_number = ""

            if not done:
                ads.used_by_owner = False

                try:
                    ads.save()
                except Exception:
                    print("oops, ads %s" % ads.id)

        for item in handled.values():
            if not item["emails"]:
                continue
            print("%s;%s" % (item["ads"].id, ";".join(item["emails"])))
