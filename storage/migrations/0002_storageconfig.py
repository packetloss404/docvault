from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('storage', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='StorageConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('enabled', models.BooleanField(default=False, help_text='Use this configuration instead of the environment settings.')),
                ('backend', models.CharField(choices=[('local', 'Local filesystem'), ('s3', 'Amazon S3'), ('b2', 'Backblaze B2'), ('minio', 'MinIO'), ('r2', 'Cloudflare R2')], default='local', max_length=16)),
                ('bucket_name', models.CharField(blank=True, default='', max_length=255)),
                ('endpoint_url', models.URLField(blank=True, default='', help_text='Required for B2, MinIO and R2. Leave blank for Amazon S3.')),
                ('region', models.CharField(blank=True, default='us-east-1', max_length=64)),
                ('access_key', models.CharField(blank=True, default='', max_length=255)),
                ('secret_key', models.CharField(blank=True, default='', max_length=512)),
                ('prefix', models.CharField(blank=True, default='documents', help_text='Key prefix all objects are stored under.', max_length=255)),
                ('addressing_style', models.CharField(blank=True, choices=[('auto', 'Auto'), ('path', 'Path-style'), ('virtual', 'Virtual-hosted')], default='', help_text='Leave blank to use the provider default.', max_length=8)),
                ('disable_checksums', models.BooleanField(blank=True, default=None, help_text='Blank uses the provider default. B2, MinIO and R2 reject the checksum headers boto3 sends by default and need this on.', null=True)),
                ('auto_create_bucket', models.BooleanField(default=False, help_text='Create the bucket if missing. Needs broader credentials.')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='storage_config_updates', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'storage configuration',
                'verbose_name_plural': 'storage configuration',
            },
        ),
    ]
