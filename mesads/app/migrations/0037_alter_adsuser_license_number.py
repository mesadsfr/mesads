# Generated by Django 4.0.5 on 2023-01-26 10:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0036_alter_ads_eco_vehicle_alter_ads_owner_name_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='adsuser',
            name='license_number',
            field=models.CharField(blank=True, default='', max_length=64),
            preserve_default=False,
        ),
    ]
