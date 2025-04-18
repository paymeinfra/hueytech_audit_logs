"""
Migration to update the method field in GunicornLogModel.
"""
# Generated by Django 3.2.16 on 2023-01-10 14:22

try:
    from django.db import migrations, models
except ImportError:
    # Mock imports for linting purposes
    migrations = models = None


class Migration(migrations.Migration):

    dependencies = [
        ('django_gunicorn_audit_logs', '0002_gunicornlogmodel'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gunicornlogmodel',
            name='method',
            field=models.CharField(
                choices=[
                    ('GET', 'GET'),
                    ('POST', 'POST'),
                    ('PUT', 'PUT'),
                    ('DELETE', 'DELETE'),
                    ('PATCH', 'PATCH'),
                    ('OPTIONS', 'OPTIONS'),
                    ('HEAD', 'HEAD'),
                ],
                db_index=True,
                max_length=20
            ),
        ),
    ]
