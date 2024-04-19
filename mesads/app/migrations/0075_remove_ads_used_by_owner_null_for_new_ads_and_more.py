# Generated by Django 4.1.9 on 2024-03-11 10:53

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0074_fix_adsuser"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="ads",
            name="used_by_owner_null_for_new_ads",
        ),
        migrations.RemoveConstraint(
            model_name="ads",
            name="owner_license_number_empty_if_not_used_by_owner",
        ),
        migrations.RemoveField(
            model_name="ads",
            name="owner_license_number",
        ),
        migrations.RemoveField(
            model_name="ads",
            name="used_by_owner",
        ),
        migrations.AlterField(
            model_name="adsuser",
            name="status",
            field=models.CharField(
                blank=True,
                choices=[
                    (
                        "titulaire_exploitant",
                        "Le titulaire de l'ADS (personne physique)",
                    ),
                    (
                        "legal_representative",
                        "Le représentant légal de la société titulaire de l'ADS (gérant ou président non salarié)",
                    ),
                    ("salarie", "Salarié du titulaire de l'ADS"),
                    ("cooperateur", "Le locataire-coopérateur de l'ADS"),
                    ("locataire_gerant", "Le locataire-gérant de l'ADS"),
                ],
                max_length=255,
                verbose_name="Modalité d'exploitation de l'ADS",
            ),
        ),
    ]