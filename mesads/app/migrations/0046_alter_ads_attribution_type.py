# Generated by Django 4.1.6 on 2023-03-10 15:45

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0045_alter_adslegalfile_options_and_more"),
    ]

    operations = [
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
                verbose_name="Type d'attribution de l'ADS",
            ),
        ),
    ]
