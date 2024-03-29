# Generated by Django 4.0.5 on 2022-10-17 10:27

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import mesads.app.models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("app", "0019_remove_adsmanageradministrator_ads_managers"),
    ]

    operations = [
        migrations.CreateModel(
            name="ADSUpdateFile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("creation_date", models.DateTimeField(auto_now_add=True)),
                (
                    "update_file",
                    models.FileField(
                        blank=True,
                        upload_to=mesads.app.models.ADSUpdateFile.get_update_filename,
                    ),
                ),
                ("imported", models.BooleanField(default=False)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
