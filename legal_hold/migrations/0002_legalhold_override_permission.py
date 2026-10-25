from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("legal_hold", "0001_initial")]

    operations = [
        migrations.AlterModelOptions(
            name="legalhold",
            options={
                "ordering": ["-created_at"],
                "verbose_name": "legal hold",
                "verbose_name_plural": "legal holds",
                "permissions": [("override_hold", "Can override document preservation under legal hold")],
            },
        ),
    ]
