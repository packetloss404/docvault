from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sources', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='source',
            name='configuration',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Source-type-specific configuration (staging path, S3 bucket, etc.).',
            ),
        ),
    ]
