# Generated by Django 5.0.6 on 2025-03-08 17:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0090_remove_ads_unique_ads_number_ads_deleted_at_and_more"),
        ("fradm", "0005_alter_commune_unique_together_and_more"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="ads",
            name="unique_ads_number",
        ),
        migrations.AddConstraint(
            model_name="ads",
            constraint=models.UniqueConstraint(
                condition=models.Q(("deleted_at__isnull", True)),
                fields=("number", "ads_manager_id"),
                name="unique_ads_number",
                violation_error_message="Une ADS avec ce numéro existe déjà. Supprimez l'ADS existante, ou utilisez un autre numéro.",
            ),
        ),
    ]
