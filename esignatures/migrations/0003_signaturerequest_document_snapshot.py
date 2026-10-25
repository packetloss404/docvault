from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("esignatures", "0002_signer_verified_phone_number")]

    operations = [
        migrations.AddField(
            model_name="signaturerequest",
            name="document_snapshot",
            field=models.JSONField(blank=True, db_default={}, default=dict, editable=False),
        ),
    ]
