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
from django.db import DatabaseError

from gunicorn.glogging import Logger
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.utils import timezone

from .choices import AGENT_STRING_MAX_LENGTH, UsageLogMethodChoices
from .models import GunicornLogModel

logger = logging.getLogger(__name__)

# Constants
SESSION_COOKIE_RE = re.compile(r"\bsessionid=(\w+)\b")
MAX_RECORD_LIFE = timedelta(days=120)  # Duration before record get expired (and deleted)


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


class GLogger(Logger):
    """
    Custom Gunicorn logger that logs requests to the database.
    """
    # We delete old records after 100 access operations
    db_check_counter = 0
    
    def __init__(self, cfg):
        super(GLogger, self).__init__(cfg)
        self.user_class = get_user_model()
        
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
            logger.warning("Failed to create log directory: %s", e)
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
            formatter = logging.Formatter(
                '%(asctime)s [%(process)d] [%(levelname)s] %(message)s',
                '%Y-%m-%d %H:%M:%S %z'
            )
            handler.setFormatter(formatter)
            file_logger.addHandler(handler)
        except (OSError, IOError) as e:
            logger.warning("Failed to set up rotating file handler: %s", e)
        
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
        if "AUTHORIZATION" in headers:
            try:
                token = headers["AUTHORIZATION"].split(" ")[-1]
                from rest_framework_simplejwt.tokens import AccessToken
                decoded_token = AccessToken(token)
                try:
                    uid = self.user_class.objects.values_list("pk", flat=True).get(pk=decoded_token.get("user_id"))
                except self.user_class.DoesNotExist:
                    raise ValueError("User doesn't exist")
            except (ValueError, TypeError, AttributeError, KeyError) as e:
                logger.warning("Failed to decode token: %s", e)
                uid = None
        elif "sessionid" in headers.get("COOKIE", ""):
            try:
                session_ids = SESSION_COOKIE_RE.findall(headers["COOKIE"])
                if not session_ids:
                    raise ValueError("User doesn't exist")
                token = session_ids[0]
                try:
                    session = Session.objects.get(session_key=token)
                    uid = session.get_decoded()["_auth_user_id"]
                except Session.DoesNotExist:
                    raise ValueError("User doesn't exist")
            except (ValueError, TypeError, AttributeError, KeyError) as e:
                logger.warning("Failed to get user from session: %s", e)
                uid = None
        else:
            uid = None

        return {"user_id": uid}

    @staticmethod
    def cache_request_body(request, headers):
        """
        Cache the request body for later use.
        
        Args:
            request: The request object
            headers: Request headers
        """
        content_length = int(headers.get('CONTENT-LENGTH', 0))
        # We don't support multipart form data since we can't parse it
        body = ""
        if 0 < content_length < 16384:
            try:
                # Read request's body, then store it in body.buf so that django can access it
                body = request.body.read()
                request.body.buf.write(body)
                request.body.buf.seek(0)
            except (IOError, AttributeError) as e:
                logger.warning("Failed to cache request body: %s", e)
        request.body.cache = body

    def process_request(self, req, headers):
        """
        Process the request and store it in the database.
        
        Args:
            req: The request object
            headers: Request headers
        """
        try:
            # Censor passwords in request body
            def censor_passwords(body, data=None):
                """
                Find all keys that have the word password in them and hide their values.
                
                Args:
                    body: The request body
                    data: The data to censor
                    
                Returns:
                    str: JSON string with censored passwords
                """
                if not data:
                    try:
                        if isinstance(body, bytes):
                            body = body.decode("utf-8")
                        data = json.loads(body)
                    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
                        return body
                
                if isinstance(data, dict):
                    for key in list(data.keys()):
                        if isinstance(data[key], (dict, list)):
                            data[key] = censor_passwords("", data[key])
                        elif isinstance(key, str) and "password" in key.lower():
                            data[key] = "********"
                elif isinstance(data, list):
                    for i, item in enumerate(data):
                        if isinstance(item, (dict, list)):
                            data[i] = censor_passwords("", item)
                
                return json.dumps(data)
            
            # Get user info
            user_info = self.get_user_info(headers, req)
            
            # Get request body
            body = getattr(req.body, "cache", "") or ""
            
            # Process request data
            try:
                if body and isinstance(body, bytes):
                    body = body.decode("utf-8")
                    body = censor_passwords(body)
            except (UnicodeDecodeError, ValueError, AttributeError) as e:
                logger.warning("Failed to process request body: %s", e)
                body = ""
            
            # Create log entry
            GunicornLogModel.objects.create(
                method=req.method,
                url=req.path,
                host=headers.get("HOST", ""),
                user_id=user_info.get("user_id"),
                user_ip=req.remote_addr,
                agent=headers.get("USER-AGENT", "")[:AGENT_STRING_MAX_LENGTH],
                source=headers.get("REFERER", ""),
                request={"body": body, "headers": strip_newlines(headers)},
                headers=strip_newlines(headers),
            )
            
            # Clean up old records
            self.db_check_counter += 1
            if self.db_check_counter >= 100:
                self.db_check_counter = 0
                expiry_date = timezone.now() - MAX_RECORD_LIFE
                GunicornLogModel.objects.filter(timestamp__lt=expiry_date).delete()
        except (ValueError, TypeError, AttributeError, KeyError, DatabaseError) as e:
            logger.warning("Failed to process request: %s", e)
    
    def process_response(self, request, response, request_time):
        """
        Update the log entry with response data.
        
        Args:
            request: The request object
            response: The response object
            request_time: The request processing time
        """
        try:
            # Get response data
            headers = dict(response.headers)
            body = getattr(response, "body", "") or ""
            
            # Process response data
            try:
                if body and isinstance(body, bytes):
                    body = body.decode("utf-8")
            except (UnicodeDecodeError, ValueError, AttributeError) as e:
                logger.warning("Failed to process response body: %s", e)
                body = ""
            
            # Update log entry
            GunicornLogModel.objects.filter(
                method=request.method,
                url=request.path,
                user_ip=request.remote_addr,
            ).update(
                response={"body": body, "headers": strip_newlines(headers)},
                duration=int(request_time * 1000000),  # Convert to microseconds
                code=response.status,
            )
            
            # Clean up old records
            self.db_check_counter += 1
            if self.db_check_counter >= 100:
                self.db_check_counter = 0
                expiry_date = timezone.now() - MAX_RECORD_LIFE
                GunicornLogModel.objects.filter(timestamp__lt=expiry_date).delete()
        except (ValueError, TypeError, AttributeError, KeyError, DatabaseError) as e:
            logger.warning("Failed to update log entry: %s", e)

    def store_to_db(self, request, request_time=None, response=None):
        """
        Store request and response data to the database.
        
        Args:
            request: The request object
            request_time: The request processing time
            response: The response object
        """
        def _save_db(self, request, request_time, response, headers):
            try:
                if response:
                    self.process_response(request, response, request_time)
                else:
                    self.process_request(request, headers)
            except (ValueError, TypeError, AttributeError, KeyError) as e:
                logger.warning("Failed to save to database: %s", e)

        headers = dict(request.headers)
        db_thread = threading.Thread(target=_save_db, args=(self, request, request_time, response, headers))
        if not response:
            # Cache request body before starting the thread otherwise django app may
            # read the body before we get chance to access it
            try:
                self.cache_request_body(request, headers)
            except (IOError, AttributeError) as e:
                logger.warning("Failed to cache request body: %s", e)
            request.__dict__["thread"] = db_thread

        db_thread.start()

    def access(self, resp, req, environ, request_time):
        """
        Log access to the database.
        
        Args:
            resp: The response object
            req: The request object
            environ: The WSGI environment
            request_time: The request processing time
        """
        # Call parent access method to log to console/file based on Gunicorn config
        super(GLogger, self).access(resp, req, environ, request_time)
        
        # Log to our custom rotating file handler
        try:
            status = resp.status
            request_line = '{method} {uri} HTTP/{http_version}'.format(
                method=req.method,
                uri=req.uri,
                http_version=environ.get('SERVER_PROTOCOL', '').split('/')[-1] or '1.0'
            )
            user_agent = req.headers.get('user-agent', '-')
            referer = req.headers.get('referer', '-')
            remote_addr = req.remote_addr or '-'
            
            log_line = '{remote_addr} - "{request_line}" {status} {response_length} "{referer}" "{user_agent}" {request_time_ms}ms'.format(
                remote_addr=remote_addr,
                request_line=request_line,
                status=status,
                response_length=resp.response_length or '-',
                referer=referer,
                user_agent=user_agent,
                request_time_ms=int(request_time * 1000)
            )
            
            self.file_logger.info(log_line)
        except (ValueError, TypeError, AttributeError, KeyError) as e:
            logger.warning("Failed to log to file: %s", e)
        
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
def on_starting(server):
    """
    Server hook for when the server starts.
    
    Args:
        server: The server instance
    """
    try:
        logger.info("Starting Gunicorn server")
    except (ValueError, TypeError, AttributeError, KeyError) as e:
        logger.warning("Error in on_starting hook: %s", e)


def post_fork(server, worker):
    """
    Server hook for after a worker has been forked.
    
    Args:
        server: The server instance
        worker: The worker instance
    """
    try:
        logger.info("Worker forked (pid: %s)", worker.pid)
    except (ValueError, TypeError, AttributeError, KeyError) as e:
        logger.warning("Error in post_fork hook: %s", e)


def pre_fork(server, worker):
    """
    Server hook for before a worker is forked.
    
    Args:
        server: The server instance
        worker: The worker instance
    """
    # No operation needed, but keeping the hook for potential future use
    pass


def pre_exec(server):
    """
    Server hook for just before a new master process is forked.
    
    Args:
        server: The server instance
    """
    try:
        logger.info("Forking master process")
    except (ValueError, TypeError, AttributeError, KeyError, SystemExit) as e:
        logger.warning("Error in pre_exec hook: %s", e)
