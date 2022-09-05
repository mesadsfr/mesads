# Generated by Django 4.0.5 on 2022-09-05 08:34

from django.db import migrations


def fill_ads_manager(apps, schema_editor):
    ADSManager = apps.get_model('app', 'ADSManager')
    for ads_manager in ADSManager.objects.all():
        administrators = ads_manager.adsmanageradministrator_set.all()
        if len(administrators) > 1:
            raise ValueError(
                f'Unable to perform migration: {ads_manager} has more than one ADSManagerAdministrator entry'
            )
        if not len(administrators):
            continue

        ads_manager.administrator = administrators[0]
        ads_manager.save()


def revert_fill_ads_manager(apps, schema_editor):
    ADSManager = apps.get_model('app', 'ADSManager')
    ADSManager.objects.update(administrator=None)


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0017_adsmanager_administrator'),
    ]

    operations = [
        migrations.RunPython(fill_ads_manager, revert_fill_ads_manager),
    ]