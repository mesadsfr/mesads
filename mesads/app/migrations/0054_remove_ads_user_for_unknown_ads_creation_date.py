# Generated by Django 4.1.7 on 2023-03-30 11:50

from django.db import migrations


def delete_ads_user_for_unknown_ads_creation_date(apps, schema_editor):
    ADSUser = apps.get_model("app", "ADSUser")

    for ads_user in ADSUser.objects.filter(ads__ads_creation_date__isnull=True):
        ads_user.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0053_ads_used_by_owner_null_for_new_ads"),
    ]

    operations = [
        migrations.RunPython(delete_ads_user_for_unknown_ads_creation_date),
    ]
