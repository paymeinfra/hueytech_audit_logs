"""
Initial migration for the Django Audit Logger package.
"""
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='RequestLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('method', models.CharField(db_index=True, max_length=10)),
                ('path', models.TextField(db_index=True)),
                ('query_params', models.TextField(blank=True, null=True)),
                ('headers', models.JSONField(default=dict)),
                ('body', models.TextField(blank=True, null=True)),
                ('content_type', models.CharField(blank=True, max_length=100, null=True)),
                ('status_code', models.IntegerField(db_index=True)),
                ('response_headers', models.JSONField(default=dict)),
                ('response_body', models.TextField(blank=True, null=True)),
                ('response_time_ms', models.IntegerField(null=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, db_index=True, null=True)),
                ('user_id', models.CharField(blank=True, db_index=True, max_length=255, null=True)),
                ('user_agent', models.TextField(blank=True, null=True)),
                ('session_id', models.CharField(blank=True, max_length=255, null=True)),
                ('extra_data', models.JSONField(blank=True, default=dict, null=True)),
            ],
            options={
                'verbose_name': 'Request Log',
                'verbose_name_plural': 'Request Logs',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='requestlog',
            index=models.Index(fields=['timestamp', 'path'], name='django_audi_timesta_e8c119_idx'),
        ),
        migrations.AddIndex(
            model_name='requestlog',
            index=models.Index(fields=['user_id', 'timestamp'], name='django_audi_user_id_5fbf30_idx'),
        ),
        migrations.AddIndex(
            model_name='requestlog',
            index=models.Index(fields=['status_code', 'timestamp'], name='django_audi_status__d01f6b_idx'),
        ),
    ]
