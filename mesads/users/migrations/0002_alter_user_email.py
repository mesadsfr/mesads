# Generated by Django 4.0.5 on 2023-01-26 10:44

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(
                error_messages={"unique": "Un utilisateur avec cet email existe déjà."},
                max_length=254,
                unique=True,
                verbose_name="email address",
            ),
        ),
    ]
