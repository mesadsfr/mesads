# Generated by Django 4.1.6 on 2023-03-14 14:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0048_alter_ads_attribution_reason'),
    ]

    operations = [
        migrations.AddField(
            model_name='adsupdatefile',
            name='import_output',
            field=models.TextField(blank=True, verbose_name="Output du script d'import du fichier"),
        ),
    ]