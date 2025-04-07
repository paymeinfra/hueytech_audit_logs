"""
Gunicorn configuration file for Django Audit Logger.

This file provides a production-ready Gunicorn configuration with:
1. Proper logging setup with file rotation
2. Performance optimizations
3. Error handling

Usage:
    gunicorn -c django_audit_logger/gunicorn_config.py your_project.wsgi:application
"""
import os
import logging
import logging.handlers
import multiprocessing

# Gunicorn configuration
bind = os.getenv('GUNICORN_BIND', '0.0.0.0:8000')
workers = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = os.getenv('GUNICORN_WORKER_CLASS', 'sync')
worker_connections = int(os.getenv('GUNICORN_WORKER_CONNECTIONS', 1000))
timeout = int(os.getenv('GUNICORN_TIMEOUT', 30))
keepalive = int(os.getenv('GUNICORN_KEEPALIVE', 2))
max_requests = int(os.getenv('GUNICORN_MAX_REQUESTS', 1000))
max_requests_jitter = int(os.getenv('GUNICORN_MAX_REQUESTS_JITTER', 50))

# Logging configuration
log_level = os.getenv('GUNICORN_LOG_LEVEL', 'info')
accesslog = os.getenv('GUNICORN_ACCESS_LOG', '-')  # '-' means stdout
errorlog = os.getenv('GUNICORN_ERROR_LOG', '-')    # '-' means stderr
access_log_format = os.getenv(
    'GUNICORN_ACCESS_LOG_FORMAT',
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(L)s'
)

# File logging setup (if not using stdout/stderr)
log_dir = os.getenv('GUNICORN_LOG_DIR', '/var/log/gunicorn')
log_max_bytes = int(os.getenv('GUNICORN_LOG_MAX_BYTES', 1024 * 1024 * 10))  # 10 MB
log_backup_count = int(os.getenv('GUNICORN_LOG_BACKUP_COUNT', 5))


def on_starting(server):
    """
    Execute when the master process is initialized.
    """
    # Create log directory if it doesn't exist and if not using stdout/stderr
    if accesslog != '-' or errorlog != '-':
        os.makedirs(log_dir, exist_ok=True)


def post_fork(server, worker):
    """
    Execute after a worker has been forked.
    """
    # Reset logger handlers to avoid duplicate logs
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)


def setup_loggers():
    """
    Set up file rotation for the logs.
    """
    try:
        if accesslog and accesslog != '-':
            access_handler = logging.handlers.RotatingFileHandler(
                accesslog,
                maxBytes=log_max_bytes,
                backupCount=log_backup_count
            )
            access_logger = logging.getLogger('gunicorn.access')
            access_logger.addHandler(access_handler)
            
        if errorlog and errorlog != '-':
            error_handler = logging.handlers.RotatingFileHandler(
                errorlog,
                maxBytes=log_max_bytes,
                backupCount=log_backup_count
            )
            error_logger = logging.getLogger('gunicorn.error')
            error_logger.addHandler(error_handler)
            
            # Also handle application logger
            app_handler = logging.handlers.RotatingFileHandler(
                os.path.join(log_dir, 'application.log'),
                maxBytes=log_max_bytes,
                backupCount=log_backup_count
            )
            app_logger = logging.getLogger('django_audit_logger')
            app_logger.addHandler(app_handler)
    except Exception as e:
        # Log to stderr if there's an issue setting up file logging
        logging.exception("Failed to set up log handlers: %s", e)


def when_ready(server):
    """
    Execute when the server is ready to receive requests.
    """
    setup_loggers()
    logging.info("Gunicorn server is ready to receive requests")
