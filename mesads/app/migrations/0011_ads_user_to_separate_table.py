# Generated by Django 4.0.5 on 2022-07-05 15:48

from django.db import migrations
from django.db.models import Count


def upgrade_migration(apps, schema_editor):
    ADS = apps.get_model("app", "ADS")
    ADSUser = apps.get_model("app", "ADSUser")
    ADSUser.objects.all().delete()
    for ads in ADS.objects.exclude(user_name="", user_siret=""):
        ads_user = ADSUser.objects.create(
            ads=ads, status=ads.user_status, name=ads.user_name, siret=ads.user_siret
        )
        ads_user.save()


def downgrade_migration(apps, schema_editor):
    ADSUser = apps.get_model("app", "ADSUser")

    count = (
        ADSUser.objects.values("ads_id")
        .annotate(count=Count("id"))
        .filter(count__gt=1)
        .count()
    )
    if count:
        raise ValueError(
            "Impossible to run this downgrade migration because at least one ADS has more than one entry in ADSUser."
        )

    for ads_user in ADSUser.objects.all():
        ads_user.ads.user_status = ads_user.status
        ads_user.ads.user_name = ads_user.name
        ads_user.ads.user_siret = ads_user.siret
        ads_user.ads.save()


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0010_adsuser"),
    ]

    operations = [
        migrations.RunPython(upgrade_migration, downgrade_migration),
    ]
