# Generated by Django 5.0.6 on 2025-04-10 18:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0009_alter_userauditentry_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="otp_secret",
            field=models.CharField(blank=True, max_length=64),
        ),
    ]
