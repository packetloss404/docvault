import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0004_document_is_held'),
        ('organization', '0003_fix_value_bool_blank'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='suggested_correspondent',
            field=models.ForeignKey(
                blank=True,
                help_text='Correspondent suggested by the ML classifier.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='+',
                to='organization.correspondent',
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='suggested_document_type',
            field=models.ForeignKey(
                blank=True,
                help_text='Document type suggested by the ML classifier.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='+',
                to='documents.documenttype',
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='suggested_tags',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='List of tag IDs suggested by the ML classifier.',
            ),
        ),
    ]
