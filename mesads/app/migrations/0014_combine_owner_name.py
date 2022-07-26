# Generated by Django 4.0.5 on 2022-07-26 14:09

from django.db import migrations


def combine_names(apps, schema_editor):
    # We can't import the Person model directly as it may be a newer
    # version than this migration expects. We use the historical version.
    ADS = apps.get_model('app', 'ADS')
    for ads in ADS.objects.all():
        combined = '%s %s' % (ads.owner_lastname, ads.owner_firstname)
        ads.owner_name = combined.strip()
        ads.save()


def revert_combine_names(apps, schema_editor):
    ADS = apps.get_model('app', 'ADS')
    ADS.objects.update(owner_name='')


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0013_ads_owner_name'),
    ]

    operations = [
        migrations.RunPython(combine_names, revert_combine_names),
    ]
