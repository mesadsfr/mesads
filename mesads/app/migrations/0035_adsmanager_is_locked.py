# Generated by Django 4.0.5 on 2023-01-18 09:02

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0034_adsmanageradministrator_expected_count"),
    ]

    operations = [
        migrations.AddField(
            model_name="adsmanager",
            name="is_locked",
            field=models.BooleanField(
                default=False,
                help_text="Cochez cette case pour empêcher la gestion manuelle des ADS pour cette administration",
            ),
        ),
    ]
