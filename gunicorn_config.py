"""
Custom Gunicorn configuration file that works with django_audit_logger.
"""
import os
import logging
import multiprocessing
from logging.handlers import RotatingFileHandler

# Basic Gunicorn configuration
bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:8000')
workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'sync'
timeout = 120
keepalive = 5
max_requests = int(os.environ.get('GUNICORN_MAX_REQUESTS', 1000))
max_requests_jitter = int(os.environ.get('GUNICORN_MAX_REQUESTS_JITTER', 50))

# Logging configuration
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')
accesslog = os.environ.get('GUNICORN_ACCESS_LOG', '-')
errorlog = os.environ.get('GUNICORN_ERROR_LOG', '-')

# Process naming
proc_name = 'payme_utils'
default_proc_name = 'payme_utils'

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Server mechanics
graceful_timeout = 30

# Custom logger class that defers Django imports
class DeferredGLogger:
    """
    A factory function that returns the GLogger class from django_audit_logger.
    This defers the import of Django models until after Django is initialized.
    """
    def __call__(self, cfg):
        from django_audit_logger.gunicorn_config import GLogger
        return GLogger(cfg)

# Use our deferred logger class
logger_class = DeferredGLogger()

# Server hooks
def on_starting(server):
    """
    Server hook for when the server starts.
    """
    logger = logging.getLogger('gunicorn.error')
    logger.info("Starting Gunicorn server with django_audit_logger")

def post_fork(server, worker):
    """
    Server hook for after a worker has been forked.
    """
    logger = logging.getLogger('gunicorn.error')
    logger.info(f"Worker forked (pid: {worker.pid})")

def worker_init(worker):
    """
    Initialize the worker after it's been forked.
    This is where we can safely import Django components.
    """
    logger = logging.getLogger('gunicorn.error')
    logger.info(f"Initializing worker {worker.pid}")
    
    # Now it's safe to import Django components
    try:
        from django.conf import settings
        from django_audit_logger.models import GunicornLogModel
        logger.info("Successfully imported Django models")
    except Exception as e:
        logger.error(f"Error importing Django models: {e}")
