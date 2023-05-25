from mesads.app.models import ADS
from mesads.app import reversion_diff


if __name__ in ("__main__", "django.core.management.commands.shell"):
    ads = ADS.objects.get(id=27389)
    revisions_diff = reversion_diff.ModelHistory(ads).get_revisions()

    for revision, objects in revisions_diff:
        print(f"{revision.date_created}")
        for cls, objects_ids in objects.items():
            print(f"\t{cls}")
            for object_id, diff in objects_ids.items():
                print("\t\t", object_id, diff)
