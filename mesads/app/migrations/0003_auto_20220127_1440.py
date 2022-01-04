# Generated by Django 3.2.9 on 2022-01-27 13:40

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('app', '0002_auto_20220117_1803'),
    ]

    operations = [
        migrations.AddField(
            model_name='adsmanagerrequest',
            name='accepted',
            field=models.BooleanField(default=None, null=True),
        ),
        migrations.AlterUniqueTogether(
            name='adsmanagerrequest',
            unique_together={('user', 'ads_manager')},
        ),
    ]
