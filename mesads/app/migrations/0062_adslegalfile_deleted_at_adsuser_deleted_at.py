# Generated by Django 4.1.9 on 2023-06-02 14:15

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0061_alter_adsuser_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="adslegalfile",
            name="deleted_at",
            field=models.DateTimeField(
                blank=True,
                default=None,
                help_text="Date de suppression de l'objet. Si cette date est renseignée, l'objet est considéré comme supprimé.",
                null=True,
                verbose_name="Date de suppression",
            ),
        ),
        migrations.AddField(
            model_name="adsuser",
            name="deleted_at",
            field=models.DateTimeField(
                blank=True,
                default=None,
                help_text="Date de suppression de l'objet. Si cette date est renseignée, l'objet est considéré comme supprimé.",
                null=True,
                verbose_name="Date de suppression",
            ),
        ),
    ]
