# Generated by Django 3.2.9 on 2022-04-25 16:13

from django.db import migrations, models
import mesads.app.models


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0005_alter_adsmanager_options"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ads",
            name="owner_siret",
            field=models.CharField(
                blank=True,
                max_length=128,
                validators=[mesads.app.models.validate_siret],
            ),
        ),
        migrations.AlterField(
            model_name="ads",
            name="user_siret",
            field=models.CharField(
                blank=True,
                max_length=128,
                validators=[mesads.app.models.validate_siret],
            ),
        ),
    ]
