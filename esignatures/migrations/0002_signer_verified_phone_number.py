"""Add verified, phone_number fields to Signer; shrink verification_code to max_length=6."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("esignatures", "0001_initial"),
    ]

    operations = [
        # Tighten verification_code from max_length=16 to 6
        migrations.AlterField(
            model_name="signer",
            name="verification_code",
            field=models.CharField(blank=True, default="", max_length=6),
        ),
        # Add verified flag
        migrations.AddField(
            model_name="signer",
            name="verified",
            field=models.BooleanField(
                default=False,
                help_text="True once the signer has verified their identity via the verification code.",
            ),
        ),
        # Add phone_number for future SMS integration
        migrations.AddField(
            model_name="signer",
            name="phone_number",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Phone number for future SMS verification. Currently unused.",
                max_length=20,
            ),
        ),
    ]
