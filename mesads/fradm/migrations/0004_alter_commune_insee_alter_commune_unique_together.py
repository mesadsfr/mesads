# Generated by Django 5.0.6 on 2024-07-05 09:45

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("fradm", "0003_alter_commune_unique_together_commune_type_commune"),
    ]

    operations = [
        migrations.AlterField(
            model_name="commune",
            name="insee",
            field=models.CharField(max_length=16),
        ),
        migrations.AlterUniqueTogether(
            name="commune",
            unique_together={("type_commune", "insee")},
        ),
    ]