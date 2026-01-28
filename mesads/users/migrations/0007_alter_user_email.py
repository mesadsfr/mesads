from django.contrib.postgres.operations import CreateCollation
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0006_remove_user_unique_ci_email"),
    ]

    operations = [
        CreateCollation(
            "case_insensitive",
            provider="icu",
            locale="und-u-ks-level2",
            deterministic=False,
        ),
        migrations.RunSQL(
            "DROP INDEX IF EXISTS \"users_user_email_243f6e77_like\";"
        ),
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.TextField(
                db_collation="case_insensitive",
                error_messages={"unique": "Un utilisateur avec cet email existe déjà."},
                unique=True,
                verbose_name="email address",
            ),
        ),
    ]
