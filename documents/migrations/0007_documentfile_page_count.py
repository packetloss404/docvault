from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0006_remove_document_suggested_correspondent_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="documentfile",
            name="page_count",
            field=models.PositiveIntegerField(default=0, db_default=0),
        ),
    ]
