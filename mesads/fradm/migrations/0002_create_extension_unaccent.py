# Generated by Django 4.1.6 on 2023-02-27 12:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('fradm', '0001_initial'),
    ]

    # Raw SQL operation to create the extension unaccent
    operations = [
        migrations.RunSQL('CREATE EXTENSION IF NOT EXISTS UNACCENT')
    ]