"""
App configuration for the Django Audit Logger package.
"""
from django.apps import AppConfig


class DjangoAuditLoggerConfig(AppConfig):
    """
    Configuration for the Django Audit Logger app.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'django_audit_logger'
    verbose_name = 'Django Audit Logger'
    
    def ready(self):
        """
        Perform initialization when Django starts.
        """
        # Import signals if needed
        # from . import signals
