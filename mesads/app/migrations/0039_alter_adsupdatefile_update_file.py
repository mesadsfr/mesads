# Generated by Django 4.0.9 on 2023-02-07 16:11

from django.db import migrations, models
import mesads.app.models


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0038_alter_ads_accepted_cpam_alter_ads_ads_creation_date_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="adsupdatefile",
            name="update_file",
            field=models.FileField(
                upload_to=mesads.app.models.ADSUpdateFile.get_update_filename
            ),
        ),
    ]
