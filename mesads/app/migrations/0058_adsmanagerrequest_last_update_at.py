# Generated by Django 4.1.7 on 2023-05-05 11:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0057_alter_adsuser_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='adsmanagerrequest',
            name='last_update_at',
            field=models.DateTimeField(null=True),
        ),
    ]
