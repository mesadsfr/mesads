# Generated by Django 3.2.9 on 2022-03-14 17:41

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0004_remove_adsmanager_users"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="adsmanager",
            options={
                "base_manager_name": "objects",
                "verbose_name": "Gestionnaire ADS",
                "verbose_name_plural": "Gestionnaires ADS",
            },
        ),
    ]
