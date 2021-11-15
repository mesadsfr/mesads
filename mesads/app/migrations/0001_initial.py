# Generated by Django 3.2.9 on 2021-11-15 10:44

from django.db import migrations, models
import django.db.models.deletion
import mesads.app.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Registrar',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('raison_sociale', models.CharField(blank=True, max_length=1024)),
                ('authority', models.CharField(blank=True, max_length=255)),
                ('siret', models.CharField(blank=True, max_length=128)),
                ('departement', models.CharField(blank=True, max_length=16)),
                ('address', models.CharField(blank=True, max_length=1024)),
            ],
        ),
        migrations.CreateModel(
            name='ADS',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.CharField(max_length=255)),
                ('creation_date', models.DateField(auto_now_add=True)),
                ('last_update', models.DateField(auto_now=True)),
                ('ads_creation_date', models.DateField(blank=True, null=True)),
                ('ads_type', models.CharField(blank=True, choices=[('old', 'L\'ADS a été créée avant la loi du 1er Octobre 2014 : "ancienne ADS "'), ('new', 'L\'ADS a été créée après la loi du 1er Octobre 2014 : "nouvelle ADS "')], max_length=16)),
                ('attribution_date', models.DateField(blank=True, null=True)),
                ('attribution_type', models.CharField(blank=True, choices=[('free', "Gratuitement (delivrée par l'autorité compétente)"), ('paid', 'Cession àt itre onéreux'), ('other', 'Autre')], max_length=16)),
                ('attribution_reason', models.CharField(blank=True, max_length=4096)),
                ('accepted_cpam', models.BooleanField(blank=True, null=True)),
                ('immatriculation_plate', models.CharField(blank=True, max_length=128)),
                ('vehicle_compatible_pmr', models.BooleanField(blank=True, null=True)),
                ('eco_vehicle', models.BooleanField(blank=True, null=True)),
                ('owner_firstname', models.CharField(blank=True, max_length=1024)),
                ('owner_lastname', models.CharField(blank=True, max_length=1024)),
                ('owner_siret', models.CharField(blank=True, max_length=128)),
                ('used_by_owner', models.BooleanField(blank=True, null=True)),
                ('user_status', models.CharField(blank=True, choices=[('titulaire_exploitant', 'Titulaire exploitant'), ('cooperateur', 'Coopérateur'), ('locataire_gerance', 'Locataire gérance'), ('autre', 'Autre')], max_length=255)),
                ('user_name', models.CharField(blank=True, max_length=1024)),
                ('user_siret', models.CharField(blank=True, max_length=128)),
                ('legal_file', models.FileField(blank=True, upload_to=mesads.app.models.ADS.get_legal_filename)),
                ('registrar', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.registrar')),
            ],
            options={
                'verbose_name': 'ADS',
                'verbose_name_plural': 'ADS',
            },
        ),
    ]
