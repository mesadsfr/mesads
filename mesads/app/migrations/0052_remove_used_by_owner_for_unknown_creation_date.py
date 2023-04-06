# Generated by Django 4.1.7 on 2023-03-30 11:43

from django.db import migrations


def delete_used_by_owner(apps, schema_editor):
    ADS = apps.get_model('app', 'ADS')
    for ads in ADS.objects.filter(ads_creation_date__isnull=True, used_by_owner__isnull=False):
        ads.used_by_owner = None
        ads.save()


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0051_ads_attribution_date_null_for_new_ads'),
    ]

    operations = [
        migrations.RunPython(delete_used_by_owner),
    ]