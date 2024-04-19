# Generated by Django 4.1.9 on 2024-03-01 15:09

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0071_alter_ads_ads_creation_date"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ads",
            name="owner_name",
            field=models.CharField(
                blank=True,
                help_text="Pour les nouvelles ADS, précisez le nom et le prénom du titulaire de l'ADS. Pour les anciennes ADS, précisez le nom et le prénom du titulaire de l'ADS s'il s'agit d'une personne physique, sinon indiquez la raison sociale de la personne morale.",
                max_length=1024,
                verbose_name="Titulaire de l'ADS",
            ),
        ),
    ]