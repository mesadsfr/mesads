# Generated by Django 3.2.9 on 2021-11-16 15:51

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_auto_20211115_1836'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='authoritiesusers',
            options={'verbose_name': "Utilisateur d'une autorité", 'verbose_name_plural': 'Utilisateurs des autorités'},
        ),
    ]
