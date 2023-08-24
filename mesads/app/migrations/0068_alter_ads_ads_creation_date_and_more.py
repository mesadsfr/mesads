# Generated by Django 4.1.9 on 2023-08-24 12:30

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0067_alter_adsmanager_epci_delegate_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ads",
            name="ads_creation_date",
            field=models.DateField(
                blank=True,
                help_text="Indiquer la date à laquelle l’ADS a été attribuée à un titulaire pour la première fois.",
                null=True,
                verbose_name="Date de création de l'ADS",
            ),
        ),
        migrations.AlterField(
            model_name="ads",
            name="attribution_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("free", "Délivrée par l'autorité compétente"),
                    ("paid", "Cession à titre onéreux"),
                    ("other", "Autre"),
                ],
                max_length=16,
                verbose_name="Type d'attribution de l'ADS au titulaire actuel",
            ),
        ),
    ]