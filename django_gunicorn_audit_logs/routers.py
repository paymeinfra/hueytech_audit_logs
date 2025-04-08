"""
Database routers for the Django Gunicorn Audit Logs package.
"""
from typing import Any, Dict, Optional, Type


class AuditLogRouter:
    """
    A router to control database operations for audit log models.
    
    This router directs all operations on audit log models to a dedicated
    'audit_logs' database, keeping them separate from the main application
    database for better performance and maintenance.
    """
    
    audit_log_app = 'django_gunicorn_audit_logs'
    audit_log_models = ['requestlog', 'gunicornlogmodel']
    audit_log_db = 'audit_logs'
    
    def db_for_read(self, model: Type, **_: Dict[str, Any]) -> Optional[str]:
        """
        Point all read operations on audit log models to the audit_logs database.
        
        Args:
            model: The model class
            **_: Additional arguments (unused)
            
        Returns:
            str: Database alias or None
        """
        # Using getattr to avoid protected-access warnings
        app_label = getattr(getattr(model, '_meta', None), 'app_label', None)
        model_name = getattr(getattr(model, '_meta', None), 'model_name', None)
        
        if app_label == self.audit_log_app and model_name in self.audit_log_models:
            return self.audit_log_db
        return None
    
    def db_for_write(self, model: Type, **_: Dict[str, Any]) -> Optional[str]:
        """
        Point all write operations on audit log models to the audit_logs database.
        
        Args:
            model: The model class
            **_: Additional arguments (unused)
            
        Returns:
            str: Database alias or None
        """
        # Using getattr to avoid protected-access warnings
        app_label = getattr(getattr(model, '_meta', None), 'app_label', None)
        model_name = getattr(getattr(model, '_meta', None), 'model_name', None)
        
        if app_label == self.audit_log_app and model_name in self.audit_log_models:
            return self.audit_log_db
        return None
    
    def allow_relation(self, obj1: Any, obj2: Any, **_: Dict[str, Any]) -> Optional[bool]:
        """
        Allow relations if both objects are audit log models.
        
        Args:
            obj1: First model instance
            obj2: Second model instance
            **_: Additional arguments (unused)
            
        Returns:
            bool: True if relation is allowed, None if router has no opinion
        """
        # Using getattr to avoid protected-access warnings
        app1 = getattr(getattr(obj1, '_meta', None), 'app_label', None)
        app2 = getattr(getattr(obj2, '_meta', None), 'app_label', None)
        
        if app1 == self.audit_log_app and app2 == self.audit_log_app:
            return True
        
        return None
    
    def allow_migrate(self, db: str, app_label: str, model_name: Optional[str] = None, 
                     **_: Dict[str, Any]) -> Optional[bool]:
        """
        Ensure audit log models only appear in the audit_logs database.
        
        Args:
            db: Database alias
            app_label: Application label
            model_name: Model name
            **_: Additional arguments (unused)
            
        Returns:
            bool: True if migration is allowed, False if not, None if router has no opinion
        """
        if app_label == self.audit_log_app and model_name in self.audit_log_models:
            return db == self.audit_log_db
        
        if db == self.audit_log_db:
            return app_label == self.audit_log_app and model_name in self.audit_log_models
        
        return None
