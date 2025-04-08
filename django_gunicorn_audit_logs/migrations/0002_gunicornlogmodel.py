"""
Migration to add GunicornLogModel for storing Gunicorn access logs.
"""
import json
try:
    from django.db import migrations, models
    import django.utils.timezone
except ImportError:
    # Mock imports for linting purposes
    migrations = models = django = None


class Migration(migrations.Migration):

    dependencies = [
        ('django_gunicorn_audit_logs', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='GunicornLogModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('method', models.CharField(db_index=True, max_length=10)),
                ('url', models.TextField(db_index=True)),
                ('host', models.CharField(blank=True, max_length=255, null=True)),
                ('user_id', models.CharField(blank=True, db_index=True, max_length=255, null=True)),
                ('user_ip', models.GenericIPAddressField(blank=True, db_index=True, null=True)),
                ('agent', models.TextField(blank=True, null=True)),
                ('source', models.CharField(blank=True, max_length=255, null=True)),
                ('request', models.JSONField(blank=True, default=dict, null=True)),
                ('response', models.JSONField(blank=True, default=dict, null=True)),
                ('headers', models.JSONField(blank=True, default=dict, null=True)),
                ('duration', models.FloatField(blank=True, null=True)),
                ('code', models.IntegerField(db_index=True)),
            ],
            options={
                'verbose_name': 'Gunicorn Log',
                'verbose_name_plural': 'Gunicorn Logs',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='gunicornlogmodel',
            index=models.Index(fields=['timestamp', 'url'], name='django_guni_timesta_guni_idx'),
        ),
        migrations.AddIndex(
            model_name='gunicornlogmodel',
            index=models.Index(fields=['user_id', 'timestamp'], name='django_guni_user_id_guni_idx'),
        ),
        migrations.AddIndex(
            model_name='gunicornlogmodel',
            index=models.Index(fields=['code', 'timestamp'], name='django_guni_code_guni_idx'),
        ),
    ]
