# Generated by Django 4.0.5 on 2022-07-05 16:13

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0011_ads_user_to_separate_table"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="ads",
            name="user_status",
        ),
        migrations.RemoveField(
            model_name="ads",
            name="user_name",
        ),
        migrations.RemoveField(
            model_name="ads",
            name="user_siret",
        ),
    ]
