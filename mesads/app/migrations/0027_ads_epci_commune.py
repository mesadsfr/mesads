# Generated by Django 4.0.5 on 2022-11-15 09:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('fradm', '0001_initial'),
        ('app', '0026_alter_adslegalfile_creation_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='ads',
            name='epci_commune',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.RESTRICT, to='fradm.commune'),
        ),
    ]
