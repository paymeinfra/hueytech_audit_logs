"""
Gunicorn configuration for the Django Gunicorn Audit Logs package.
"""
import os
import logging
import threading
import json
import re
from datetime import timedelta
from logging.handlers import RotatingFileHandler

# Constants
MAX_RECORD_LIFE = timedelta(days=120)  # Duration before record get expired (and deleted)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)

# Try to import Django and Gunicorn modules
# These imports may fail in certain environments (e.g., during testing)
try:
    import django.db as django_db
    from gunicorn.glogging import Logger
    import django.contrib.auth as django_auth
    from django.contrib.sessions.models import Session
    import django.utils.timezone as django_timezone
    from django.contrib.auth import get_user_model
    from .choices import AGENT_STRING_MAX_LENGTH, UsageLogMethodChoices
    from .models import GunicornLogModel
    
    # Set Django database error
    DatabaseError = django_db.Error
except ImportError as e:
    logging.warning("Django or Gunicorn import error: %s", e)
    logging.warning("Some functionality may be limited")
    
    # Define fallback classes
    class Logger:
        """Fallback Logger class when gunicorn is not available."""
        pass
    
    class DatabaseError(Exception):
        """Fallback DatabaseError class when Django is not available."""
        pass
    
    Session = None
    django_timezone = None
    get_user_model = None
    AGENT_STRING_MAX_LENGTH = None
    UsageLogMethodChoices = None
    GunicornLogModel = None

# Defer Django imports to avoid "Apps aren't loaded yet" error
def get_django_imports():
    """
    Import Django components only when needed, after Django is initialized.
    """
    try:
        from django.db import DatabaseError
        from gunicorn.glogging import Logger
        from django.contrib.auth import get_user_model
        from django.contrib.sessions.models import Session
        from django.utils import timezone
        from .choices import AGENT_STRING_MAX_LENGTH, UsageLogMethodChoices
        from .models import GunicornLogModel
        
        # Regular expression for session cookie
        SESSION_COOKIE_RE = re.compile(r"\bsessionid=(\w+)\b")
        
        return {
            'DatabaseError': DatabaseError,
            'Logger': Logger,
            'get_user_model': get_user_model,
            'Session': Session,
            'timezone': timezone,
            'AGENT_STRING_MAX_LENGTH': AGENT_STRING_MAX_LENGTH,
            'UsageLogMethodChoices': UsageLogMethodChoices,
            'GunicornLogModel': GunicornLogModel,
            'SESSION_COOKIE_RE': SESSION_COOKIE_RE
        }
    except ImportError as e:
        logging.warning("Django or Gunicorn import error: %s", e)
        logging.warning("Some functionality may be limited")
        
        # Define fallback classes
        class Logger:
            """Fallback Logger class when gunicorn is not available."""
            pass
        
        class DatabaseError(Exception):
            """Fallback DatabaseError class when Django is not available."""
            pass
        
        Session = None
        timezone = None
        AGENT_STRING_MAX_LENGTH = None
        UsageLogMethodChoices = None
        GunicornLogModel = None
        SESSION_COOKIE_RE = None
        
        return {
            'DatabaseError': DatabaseError,
            'Logger': Logger,
            'get_user_model': None,
            'Session': Session,
            'timezone': timezone,
            'AGENT_STRING_MAX_LENGTH': AGENT_STRING_MAX_LENGTH,
            'UsageLogMethodChoices': UsageLogMethodChoices,
            'GunicornLogModel': GunicornLogModel,
            'SESSION_COOKIE_RE': SESSION_COOKIE_RE
        }


def strip_newlines(data):
    """
    Remove newlines from strings in data structures.
    """
    if isinstance(data, dict):
        return {key: strip_newlines(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [strip_newlines(item) for item in data]
    elif isinstance(data, str):
        return data.replace('\n', '')
    else:
        return data


class GLogger:
    """
    Custom Gunicorn logger that logs requests to the database.
    """
    # We delete old records after 100 access operations
    db_check_counter = 0
    
    def __init__(self, cfg):
        # Import Django components when the logger is initialized
        django_imports = get_django_imports()
        self.Logger = django_imports['Logger']
        self.DatabaseError = django_imports['DatabaseError']
        self.get_user_model = django_imports['get_user_model']
        self.Session = django_imports['Session']
        self.timezone = django_imports['timezone']
        self.AGENT_STRING_MAX_LENGTH = django_imports['AGENT_STRING_MAX_LENGTH']
        self.UsageLogMethodChoices = django_imports['UsageLogMethodChoices']
        self.GunicornLogModel = django_imports['GunicornLogModel']
        self.SESSION_COOKIE_RE = django_imports['SESSION_COOKIE_RE']
        
        # Initialize the parent logger
        self.logger = self.Logger(cfg)
        
        # Get the user model
        self.user_class = self.get_user_model()
        
        # Set up file-based rotating logger for requests
        self.file_logger = self._setup_file_logger()
    
    def _setup_file_logger(self):
        """
        Set up a rotating file logger for requests.
        
        Returns:
            logging.Logger: Configured logger instance
        """
        file_logger = logging.getLogger('gunicorn.access.file')
        file_logger.propagate = False
        file_logger.setLevel(logging.INFO)
        
        # Get log directory from environment or use default
        log_dir = os.environ.get('GUNICORN_LOG_DIR', '/var/log/gunicorn')
        
        # Create log directory if it doesn't exist
        try:
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
        except (OSError, IOError) as e:
            logging.warning("Failed to create log directory: %s", e)
            # Fall back to current directory
            log_dir = '.'
        
        # Set up rotating file handler
        log_file = os.path.join(log_dir, 'gunicorn_access.log')
        max_bytes = int(os.environ.get('GUNICORN_LOG_MAX_BYTES', 10 * 1024 * 1024))  # 10MB default
        backup_count = int(os.environ.get('GUNICORN_LOG_BACKUP_COUNT', 10))  # 10 files default
        
        try:
            handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count
            )
            handler.setFormatter(logging.Formatter('%(message)s'))
            file_logger.addHandler(handler)
        except (OSError, IOError) as e:
            logging.warning("Failed to set up rotating file handler: %s", e)
        
        return file_logger
    
    def get_user_info(self, headers, _):
        """
        Get user ID from authentication token or session ID.
        
        Args:
            headers: Request headers
            _: The request object (unused)
            
        Returns:
            dict: Dictionary containing user_id
            
        Raises:
            ValueError: If user doesn't exist
        """
        user_info = {'user_id': None}
        
        try:
            # Try to get user from Authorization header
            auth_header = headers.get('authorization', '')
            if auth_header.startswith('Bearer '):
                # Extract token from Authorization header
                # Unused variable removed to fix lint error
                auth_header.split(' ')[1]
                
                # Logic to get user from token would go here
                # For now, just return None as user_id
                return user_info
                
            # Try to get user from session cookie
            cookie_header = headers.get('cookie', '')
            session_match = self.SESSION_COOKIE_RE.search(cookie_header)
            
            if session_match:
                session_key = session_match.group(1)
                try:
                    # Get session and user from session key
                    session = self.Session.objects.get(session_key=session_key)
                    uid = session.get_decoded().get('_auth_user_id')
                    if uid:
                        user = self.user_class.objects.get(pk=uid)
                        user_info['user_id'] = user.id
                except (self.DatabaseError, self.Session.DoesNotExist, self.user_class.DoesNotExist, KeyError) as e:
                    logging.debug("Session or user not found: %s", e)
        except (ValueError, AttributeError, IndexError, TypeError) as e:
            logging.debug("Error extracting user info: %s", e)
            
        return user_info
    
    def get_request_body(self, request):
        """
        Get the request body.
        
        Args:
            request: The request object
        
        Returns:
            str: The request body
        """
        try:
            return request.body.decode('utf-8')
        except (UnicodeDecodeError, AttributeError):
            return ''
    
    def process_request(self, req, headers):
        """
        Process a request.
        
        Args:
            req: The request object
            headers: The request headers
        """
        # Store request data
        req._request_data = {
            'method': req.method,
            'path': req.path,
            'query_string': req.query_string.decode('utf-8', errors='replace') if hasattr(req.query_string, 'decode') else req.query_string,
            'headers': dict(headers),
            'body': self.get_request_body(req)
        }
    
    def store_to_db(self, request, request_time=None):
        """
        Store request and response data to the database.
        
        Args:
            request: The request object
            request_time: The request processing time
        """
        # Skip if GunicornLogModel is not available
        if not self.GunicornLogModel:
            return
            
        # Skip if request doesn't have required attributes
        if not hasattr(request, 'uri') or not hasattr(request, 'headers'):
            return
            
        try:
            # Get request data
            method = getattr(request, 'method', 'UNKNOWN')
            path = request.uri
            
            # Get user info
            user_info = self.get_user_info(request.headers, request)
            user_id = user_info.get('user_id')
            
            # Get request body
            body = self.get_request_body(request)
            
            # Get IP address
            forwarded_for = request.headers.get('x-forwarded-for', '')
            if forwarded_for:
                # Get the first IP in the list
                ip_address = forwarded_for.split(',')[0].strip()
            else:
                ip_address = getattr(request, 'remote_addr', None) or '0.0.0.0'
                
            # Get user agent
            user_agent = request.headers.get('user-agent', '')
            if self.AGENT_STRING_MAX_LENGTH and len(user_agent) > self.AGENT_STRING_MAX_LENGTH:
                user_agent = user_agent[:self.AGENT_STRING_MAX_LENGTH]
                
            # Create log entry
            self.GunicornLogModel.objects.create(
                user_id=user_id,
                ip_address=ip_address,
                method=method,
                path=path,
                request_body=body,
                user_agent=user_agent,
                request_time=request_time
            )
            
            # Clean up old records
            self.db_check_counter += 1
            if self.db_check_counter >= 100:
                self.db_check_counter = 0
                cutoff_date = self.timezone.now() - MAX_RECORD_LIFE
                self.GunicornLogModel.objects.filter(created_at__lt=cutoff_date).delete()
                
        except (ValueError, AttributeError, self.DatabaseError) as e:
            logging.warning("Failed to log to database: %s", e)
    
    def access(self, resp, req, environ, request_time):
        """
        Log access to the database.
        
        Args:
            resp: The response object
            req: The request object
            environ: The WSGI environment
            request_time: The request processing time
        """
        # Skip logging for static files and health checks
        if req.path.startswith(('/static/', '/media/', '/health/', '/favicon.ico')):
            return
        
        # Process request
        try:
            # Get request headers
            headers = req.headers
            
            # Process the request
            self.process_request(req, headers)
        except (ValueError, TypeError, AttributeError) as e:
            logging.warning("Failed to process request: %s", e)
        
        # Log to file
        try:
            status = resp.status
            request_line = "%s %s %s" % (req.method, req.path, environ.get('SERVER_PROTOCOL', 'HTTP/1.1'))
            user_agent = req.headers.get('user-agent', '-')
            referer = req.headers.get('referer', '-')
            remote_addr = req.remote_addr or '-'
            
            log_line = '%s - "%s" %s %s "%s" "%s" %sms' % (
                remote_addr,
                request_line,
                status,
                resp.response_length or '-',
                referer,
                user_agent,
                int(request_time * 1000)
            )
            
            self.file_logger.info(log_line)
        except (ValueError, TypeError, AttributeError) as e:
            logging.warning("Failed to log to file: %s", e)
        
        # Store in database
        self.store_to_db(request=req, request_time=request_time)


# Gunicorn configuration
bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:8000')
workers = int(os.environ.get('GUNICORN_WORKERS', '4'))
worker_class = 'sync'
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging configuration
accesslog = os.environ.get('GUNICORN_ACCESS_LOG', '-')
errorlog = os.environ.get('GUNICORN_ERROR_LOG', '-')
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')
logger_class = 'django_gunicorn_audit_logs.gunicorn_config.GLogger'

# Additional logging configuration for file rotation
logconfig_dict = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'generic': {
            'format': '%(asctime)s [%(process)d] [%(levelname)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S %z',
            'class': 'logging.Formatter'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'generic',
            'stream': 'ext://sys.stdout'
        },
        'error_console': {
            'class': 'logging.StreamHandler',
            'formatter': 'generic',
            'stream': 'ext://sys.stderr'
        }
    },
    'loggers': {
        'gunicorn.error': {
            'level': os.environ.get('GUNICORN_LOG_LEVEL', 'info').upper(),
            'handlers': ['error_console'],
            'propagate': False,
            'qualname': 'gunicorn.error'
        }
    }
}

# Process naming
proc_name = 'django_gunicorn_audit_logs'
default_proc_name = 'django_gunicorn_audit_logs'

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Server mechanics
graceful_timeout = 30
max_requests = int(os.environ.get('GUNICORN_MAX_REQUESTS', '1000'))
max_requests_jitter = int(os.environ.get('GUNICORN_MAX_REQUESTS_JITTER', '50'))

# Server hooks
def on_starting(_server):
    """
    Server hook for when the server starts.
    
    Args:
        _server: The server instance (unused)
    """
    try:
        logging.info("Starting Gunicorn server")
    except (OSError, IOError, SystemExit) as e:
        logging.warning("Error in on_starting hook: %s", e)


def post_fork(_server, worker):
    """
    Server hook for after a worker has been forked.
    
    Args:
        _server: The server instance (unused)
        worker: The worker instance
    """
    try:
        logging.info("Worker forked (pid: %s)", worker.pid)
    except (OSError, IOError, SystemExit) as e:
        logging.warning("Error in post_fork hook: %s", e)


def pre_fork(_server, _worker):
    """
    Server hook for before a worker is forked.
    
    Args:
        _server: The server instance (unused)
        _worker: The worker instance (unused)
    """
    logging.debug("Pre-fork hook called")


def pre_exec(_server):
    """
    Server hook for just before a new master process is forked.
    
    Args:
        _server: The server instance (unused)
    """
    try:
        logging.info("Forking master process")
    except (OSError, IOError, SystemExit) as e:
        logging.warning("Error in pre_exec hook: %s", e)


def when_ready(_server):
    """
    Server hook for when the server is ready.
    
    Args:
        _server: The server instance (unused)
    """
    try:
        logging.info("Gunicorn server is ready")
    except (OSError, IOError, SystemExit) as e:
        logging.warning("Error in when_ready hook: %s", e)


def worker_int(_worker):
    """
    Server hook for when a worker is interrupted.
    
    Args:
        _worker: The worker instance (unused)
    """
    try:
        logging.info("Worker interrupted")
    except (OSError, IOError, SystemExit) as e:
        logging.warning("Error in worker_int hook: %s", e)
