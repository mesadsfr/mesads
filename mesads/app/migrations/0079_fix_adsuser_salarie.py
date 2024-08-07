# Generated by Django 4.1.9 on 2024-03-11 15:27

from django.db import migrations


def upgrade(apps, schema_editor):
    """Fix ADSUser data, see https://trello.com/c/dG9fG0wC"""
    ADSUser = apps.get_model("app", "ADSUser")

    for ads_user in ADSUser.objects.filter(status="salarie").exclude(siret="").all():
        ads_user.siret = ""
        ads_user.save()


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0078_fix_adsuser_legal_representative"),
    ]

    operations = [
        migrations.RunPython(upgrade),
    ]
