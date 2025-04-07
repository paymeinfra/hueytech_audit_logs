"""
Migration to update the method field in GunicornLogModel.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('django_audit_logger', '0002_gunicornlogmodel'),
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
