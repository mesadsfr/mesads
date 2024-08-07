# Generated by Django 5.0.6 on 2024-06-06 16:10

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0082_notification"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="ads_created_or_updated",
            field=models.BooleanField(
                default=False,
                verbose_name="Recevoir une notification lorsqu'une ADS d'une administration gérée est créée ou modifiée (pour les préfectures uniquement)",
            ),
        ),
        migrations.AlterField(
            model_name="notification",
            name="ads_manager_requests",
            field=models.BooleanField(
                default=True,
                verbose_name="Recevoir une notification lorsqu'une demande pour devenir gestionnaire ADS est créée (pour les préfectures uniquement)",
            ),
        ),
    ]
