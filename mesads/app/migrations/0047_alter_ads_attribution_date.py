# Generated by Django 4.1.6 on 2023-03-13 13:36

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0046_alter_ads_attribution_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ads",
            name="attribution_date",
            field=models.DateField(
                blank=True,
                help_text="Laissez ce champ vide si le titulaire n'a pas changé depuis la création de l'ADS.",
                null=True,
                verbose_name="Date d'attribution de l'ADS au titulaire actuel",
            ),
        ),
    ]
