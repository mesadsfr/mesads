# Generated by Django 5.0.6 on 2024-06-27 13:04

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("vehicules_relais", "0005_dispositionspecifique"),
    ]

    operations = [
        migrations.AlterField(
            model_name="vehicule",
            name="motorisation",
            field=models.CharField(
                blank=True,
                choices=[
                    ("essence", "Essence"),
                    ("diesel", "Diesel"),
                    ("hybride", "Hybride"),
                    ("hybride_rechargeable", "Hybride rechargeable"),
                    ("electrique", "Electrique"),
                    ("GPL", "GPL"),
                    ("E85", "E85"),
                    ("h2", "Hydrogène"),
                ],
                max_length=64,
                verbose_name="Motorisation du véhicule",
            ),
        ),
    ]
