"""
App configuration for the Django Gunicorn Audit Logs package.
"""
from django.apps import AppConfig


class DjangoGunicornAuditLogsConfig(AppConfig):
    """
    Configuration for the Django Gunicorn Audit Logs app.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'django_gunicorn_audit_logs'
    verbose_name = 'Django Gunicorn Audit Logs'
    
    def ready(self):
        """
        Perform initialization when Django starts.
        """
        # Import signals if needed
        # from . import signals
