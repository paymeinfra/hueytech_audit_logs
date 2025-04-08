"""
Gunicorn configuration for the Django Audit Logger package.
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

# Defer Django imports to avoid "Apps aren't loaded yet" error
def get_django_imports():
    """
    Import Django components only when needed, after Django is initialized.
    """
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
    
    def get_user_info(self, headers, request):
        """
        Get user ID from authentication token or session ID.
        
        Args:
            headers: Request headers
            request: The request object
            
        Returns:
            dict: Dictionary containing user_id
            
        Raises:
            ValueError: If user doesn't exist
        """
        user_id = None
        
        # Try to get user from Authorization header
        auth_header = headers.get('authorization', '')
        if auth_header.startswith('Token ') or auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                # This is a placeholder for token authentication
                # In a real application, you would validate the token
                # and retrieve the user ID
                pass
            except Exception:
                pass
        
        # Try to get user from session cookie
        if not user_id:
            cookie = headers.get('cookie', '')
            session_match = self.SESSION_COOKIE_RE.search(cookie)
            if session_match:
                session_key = session_match.group(1)
                try:
                    session = self.Session.objects.get(
                        session_key=session_key,
                        expire_date__gt=self.timezone.now()
                    )
                    user_id = session.get_decoded().get('_auth_user_id')
                except (self.Session.DoesNotExist, KeyError):
                    pass
        
        return {'user_id': user_id}
    
    @staticmethod
    def cache_request_body(request, headers):
        """
        Cache the request body for later use.
        
        Args:
            request: The request object
            headers: Request headers
        """
        # Only cache if content type is JSON or form data
        content_type = headers.get('content-type', '')
        if 'application/json' in content_type or 'application/x-www-form-urlencoded' in content_type:
            try:
                # Read the request body and store it in a custom attribute
                body = request.body.decode('utf-8')
                setattr(request, '_cached_body', body)
            except (UnicodeDecodeError, AttributeError):
                pass
    
    def process_request(self, req, headers):
        """
        Process the request and store it in the database.
        
        Args:
            req: The request object
            headers: Request headers
        """
        def censor_passwords(body, data=None):
            """
            Find all keys that have the word password in them and hide their values.
            
            Args:
                body: The request body
                data: The data to censor
                
            Returns:
                str: JSON string with censored passwords
            """
            if not body:
                return body
            
            if data is None:
                try:
                    data = json.loads(body)
                except (json.JSONDecodeError, TypeError):
                    return body
            
            if isinstance(data, dict):
                for key in list(data.keys()):
                    if isinstance(data[key], dict):
                        data[key] = censor_passwords(None, data[key])
                    elif isinstance(data[key], list):
                        data[key] = [censor_passwords(None, item) if isinstance(item, dict) else item for item in data[key]]
                    elif 'password' in key.lower():
                        data[key] = '********'
            
            return json.dumps(data)
        
        # Cache the request body for later use
        self.cache_request_body(req, headers)
        
        # Get the request body
        body = getattr(req, '_cached_body', None)
        
        # Censor passwords in the request body
        if body:
            body = censor_passwords(body)
        
        # Store request data in a custom attribute for later use
        setattr(req, '_request_data', {
            'method': req.method,
            'path': req.path,
            'query_string': req.query_string.decode('utf-8') if hasattr(req, 'query_string') else '',
            'headers': dict(headers),
            'body': body,
            'remote_addr': req.remote_addr
        })
    
    def process_response(self, request, response, request_time):
        """
        Update the log entry with response data.
        
        Args:
            request: The request object
            response: The response object
            request_time: The request processing time
        """
        # Get response body if available
        body = None
        if hasattr(response, 'body'):
            try:
                body = response.body.decode('utf-8')
            except (UnicodeDecodeError, AttributeError):
                pass
        
        # Get response headers
        headers = {}
        if hasattr(response, 'headers'):
            headers = dict(response.headers)
        
        # Store response data in a custom attribute for later use
        setattr(request, '_response_data', {
            'status_code': response.status,
            'headers': headers,
            'body': body,
            'request_time': request_time
        })
    
    def store_to_db(self, request, request_time=None, response=None):
        """
        Store request and response data to the database.
        
        Args:
            request: The request object
            request_time: The request processing time
            response: The response object
        """
        def _save_db(self, request, request_time, response, headers):
            # Get request data
            request_data = getattr(request, '_request_data', {})
            method = request_data.get('method', '')
            path = request_data.get('path', '')
            query_string = request_data.get('query_string', '')
            request_headers = request_data.get('headers', {})
            request_body = request_data.get('body', '')
            remote_addr = request_data.get('remote_addr', '')
            
            # Get response data
            response_data = getattr(request, '_response_data', {})
            status_code = response_data.get('status_code', 0)
            response_headers = response_data.get('response_headers', {})
            response_body = response_data.get('body', '')
            
            # Get user info
            user_info = self.get_user_info(headers, request)
            user_id = user_info.get('user_id')
            
            # Create log entry
            log_entry = self.GunicornLogModel(
                method=method,
                url=path,
                query_params=query_string,
                headers=json.dumps(strip_newlines(request_headers)),
                body=request_body,
                ip_address=remote_addr,
                user_id=user_id,
                code=status_code,
                response_headers=json.dumps(strip_newlines(response_headers)),
                response_body=response_body,
                response_time_ms=int(request_time * 1000) if request_time else None
            )
            log_entry.save()
        
        # Process response if provided
        if response and not hasattr(request, '_response_data'):
            self.process_response(request, response, request_time)
        
        # Get headers
        headers = {}
        if hasattr(request, 'headers'):
            headers = request.headers
        
        # Store to database in a separate thread to avoid blocking
        try:
            thread = threading.Thread(
                target=_save_db,
                args=(self, request, request_time, response, headers)
            )
            thread.daemon = True
            thread.start()
        except Exception as e:
            logging.warning("Failed to start thread for database logging: %s", e)
    
    def access(self, resp, req, environ, request_time):
        """
        Log access to the database.
        
        Args:
            resp: The response object
            req: The request object
            environ: The WSGI environment
            request_time: The request processing time
        """
        # Process the request if not already processed
        if not hasattr(req, '_request_data'):
            headers = req.headers
            self.process_request(req, headers)
        
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
        except (ValueError, TypeError, AttributeError, KeyError) as e:
            logging.warning("Failed to log to file: %s", e)
        
        # Store in database
        self.store_to_db(request=req, response=resp, request_time=request_time)


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
logger_class = 'django_audit_logger.gunicorn_config.GLogger'

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
proc_name = 'django_audit_logger'
default_proc_name = 'django_audit_logger'

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
    except Exception as e:
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
    except Exception as e:
        logging.warning("Error in post_fork hook: %s", e)


def pre_fork(_server, _worker):
    """
    Server hook for before a worker is forked.
    
    Args:
        _server: The server instance (unused)
        _worker: The worker instance (unused)
    """
    # No operation needed, but keeping the hook for potential future use
    pass


def pre_exec(_server):
    """
    Server hook for just before a new master process is forked.
    
    Args:
        _server: The server instance (unused)
    """
    try:
        logging.info("Forking master process")
    except Exception as e:
        logging.warning("Error in pre_exec hook: %s", e)
