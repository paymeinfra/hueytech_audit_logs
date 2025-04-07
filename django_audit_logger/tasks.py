"""
Celery tasks for asynchronous logging operations.
"""
import json
import logging
import os
import time
from typing import Dict, Any, Optional, Callable

# Flag to track if Celery is available
CELERY_AVAILABLE = False
celery_app = None

try:
    from celery import shared_task, Celery
    from celery.exceptions import OperationalError
    CELERY_AVAILABLE = True
    
    # Get a reference to the Celery app for worker checks
    try:
        from django.conf import settings
        celery_app = Celery()
        celery_app.config_from_object('django.conf:settings', namespace='CELERY')
    except (ImportError, AttributeError):
        pass
        
except ImportError:
    # Create a dummy decorator for environments without Celery
    def shared_task(*args, **kwargs):
        def decorator(func):
            return func
        return decorator if args and callable(args[0]) else decorator

from django.conf import settings
from .models import RequestLog
from .mongo_storage import mongo_storage

logger = logging.getLogger('django_audit_logger')


def are_celery_workers_running() -> bool:
    """
    Check if Celery workers are running.
    
    Returns:
        bool: True if workers are running, False otherwise
    """
    if not CELERY_AVAILABLE or celery_app is None:
        return False
        
    try:
        # Try to ping workers with a timeout
        inspector = celery_app.control.inspect()
        stats = inspector.stats()
        if stats:
            # If we get stats back, workers are running
            return True
        return False
    except (OperationalError, IOError, ConnectionRefusedError, TimeoutError):
        return False
    except Exception as e:
        logger.warning(f"Error checking Celery workers: {e}")
        return False


# Define the task parameters
task_params = {
    'bind': True,
    'max_retries': 3,
    'default_retry_delay': 60,
    'queue': os.environ.get('AUDIT_CELERY_QUEUE', 'audit_logs')
}

# Only apply task parameters if Celery is available
task_decorator = shared_task(**task_params) if CELERY_AVAILABLE else shared_task()

@task_decorator
def create_request_log_entry(
    self,
    method: str,
    path: str,
    query_params: Dict[str, Any],
    request_headers: Dict[str, Any],
    request_body: str,
    client_ip: str,
    user_id: Optional[str],
    status_code: int,
    response_headers: Dict[str, Any],
    response_body: str,
    execution_time: float
) -> None:
    """
    Create a log entry in the database asynchronously.
    
    Args:
        method: HTTP method
        path: Request path
        query_params: Query parameters
        request_headers: Request headers
        request_body: Request body
        client_ip: Client IP address
        user_id: User ID if available
        status_code: HTTP status code
        response_headers: Response headers
        response_body: Response body
        execution_time: Execution time in seconds
    """
    # Check storage configuration
    use_mongo = getattr(settings, 'AUDIT_LOGS_USE_MONGO', False)
    write_to_both = getattr(settings, 'AUDIT_LOGS_WRITE_TO_BOTH', False)
    
    try:
        # Convert dictionaries to JSON strings if they're not already
        if isinstance(query_params, dict):
            query_params = json.dumps(query_params)
        
        if isinstance(request_headers, dict):
            request_headers = json.dumps(request_headers)
            
        if isinstance(response_headers, dict):
            response_headers = json.dumps(response_headers)
        
        # Prepare log data dictionary for reuse
        log_data = {
            'method': method,
            'path': path,
            'query_params': query_params,
            'headers': request_headers,
            'body': request_body,
            'ip_address': client_ip,
            'user_id': user_id,
            'status_code': status_code,
            'response_headers': response_headers,
            'response_body': response_body,
            'response_time_ms': int(execution_time * 1000) if execution_time else None
        }
        
        # MongoDB storage logic
        mongo_success = False
        if (use_mongo or write_to_both) and mongo_storage.is_available():
            mongo_success = mongo_storage.create_request_log(**log_data)
            if mongo_success:
                logger.debug("Successfully created MongoDB log entry for %s %s", method, path)
            else:
                logger.warning("Failed to create MongoDB log entry for %s %s", method, path)
        
        # PostgreSQL storage logic
        if not use_mongo or write_to_both or (use_mongo and not mongo_success):
            RequestLog.objects.create(
                method=method,
                path=path,
                query_params=query_params,
                headers=request_headers,
                body=request_body,
                ip_address=client_ip,
                user_id=user_id,
                status_code=status_code,
                response_headers=response_headers,
                response_body=response_body,
                response_time_ms=int(execution_time * 1000) if execution_time else None
            )
            logger.debug("Successfully created PostgreSQL log entry for %s %s", method, path)
            
    except (RequestLog.DoesNotExist, RequestLog.MultipleObjectsReturned, 
            ValueError, TypeError, json.JSONDecodeError) as exc:
        # Using specific exceptions instead of broad Exception
        logger.error("Failed to create log entry: %s", exc)
        if CELERY_AVAILABLE and hasattr(self, 'retry'):
            self.retry(exc=exc)
