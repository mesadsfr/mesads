# Generated by Django 4.0.9 on 2023-02-08 10:18

from django.db import migrations, models
import django.db.models.expressions


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0039_alter_adsupdatefile_update_file'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='ads',
            constraint=models.CheckConstraint(check=models.Q(('ads_creation_date__isnull', True), ('attribution_date__isnull', True), ('ads_creation_date__lte', django.db.models.expressions.F('attribution_date')), _connector='OR'), name='ads_creation_date_before_attribution_date'),
        ),
    ]
