"""
Middleware for the Django Audit Logger package.
"""
import json
import time
import logging
from django.conf import settings
from django.utils.module_loading import import_string
from .models import RequestLog
from .utils import get_client_ip, get_user_id, mask_sensitive_data

logger = logging.getLogger(__name__)


class AuditLogMiddleware:
    """
    Middleware to log all requests and responses to the database.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.settings = getattr(settings, 'AUDIT_LOGGER', {})
        self.enabled = self.settings.get('ENABLED', True)
        self.log_request_body = self.settings.get('LOG_REQUEST_BODY', True)
        self.log_response_body = self.settings.get('LOG_RESPONSE_BODY', True)
        self.exclude_paths = self.settings.get('EXCLUDE_PATHS', [])
        self.exclude_extensions = self.settings.get('EXCLUDE_EXTENSIONS', [])
        self.max_body_length = self.settings.get('MAX_BODY_LENGTH', 10000)
        self.sensitive_fields = self.settings.get('SENSITIVE_FIELDS', 
                                                 ['password', 'token', 'access_key', 'secret'])
        
        # Load user ID callable
        user_id_callable = self.settings.get('USER_ID_CALLABLE', 'django_audit_logger.utils.get_user_id')
        self.get_user_id = import_string(user_id_callable) if isinstance(user_id_callable, str) else user_id_callable
        
        # Load extra data callable
        extra_data_callable = self.settings.get('EXTRA_DATA_CALLABLE', None)
        self.get_extra_data = import_string(extra_data_callable) if isinstance(extra_data_callable, str) and extra_data_callable else None

    def __call__(self, request):
        if not self.enabled or self._should_skip_logging(request):
            return self.get_response(request)
        
        # Start timing the request
        start_time = time.time()
        
        # Capture request data
        request_data = self._capture_request_data(request)
        
        # Get the original request body so we can restore it after reading
        if hasattr(request, 'body'):
            request._body = request.body
        
        # Process the request and capture the response
        try:
            response = self.get_response(request)
            response_data = self._capture_response_data(response)
            status_code = response.status_code
        except Exception as e:
            logger.exception("Exception in request processing: %s", e)
            response_data = {
                'headers': {},
                'body': "Error processing request",
            }
            status_code = 500
            # Re-raise the exception to let Django handle it
            raise
        finally:
            # Calculate response time
            response_time = int((time.time() - start_time) * 1000)  # in milliseconds
            
            # Create the log entry
            try:
                self._create_log_entry(request, request_data, response_data, status_code, response_time)
            except Exception as e:
                # Log the error but don't disrupt the request/response cycle
                logger.exception("Failed to create audit log entry: %s", e)
        
        return response
    
    def _should_skip_logging(self, request):
        """
        Determine if this request should be excluded from logging.
        """
        path = request.path
        
        # Check excluded paths
        for excluded_path in self.exclude_paths:
            if path.startswith(excluded_path):
                return True
        
        # Check excluded extensions
        for ext in self.exclude_extensions:
            if path.endswith(ext):
                return True
        
        return False
    
    def _capture_request_data(self, request):
        """
        Capture relevant data from the request.
        """
        headers = {}
        for key, value in request.META.items():
            if key.startswith('HTTP_'):
                header_key = key[5:].lower().replace('_', '-')
                headers[header_key] = value
            elif key in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
                header_key = key.lower().replace('_', '-')
                headers[header_key] = value
        
        # Get request body if enabled
        body = None
        if self.log_request_body and request.method not in ('GET', 'HEAD'):
            try:
                if hasattr(request, 'body'):
                    body = request.body.decode('utf-8')
                    # Mask sensitive data
                    body = mask_sensitive_data(body, self.sensitive_fields)
                    # Truncate if too long
                    if len(body) > self.max_body_length:
                        body = body[:self.max_body_length] + '... [truncated]'
            except Exception as e:
                logger.warning("Failed to capture request body: %s", e)
                body = "[Error capturing request body]"
        
        # Get query parameters
        query_params = None
        if request.GET:
            try:
                query_dict = dict(request.GET)
                # Mask sensitive data in query params
                for field in self.sensitive_fields:
                    if field in query_dict:
                        query_dict[field] = '********'
                query_params = json.dumps(query_dict)
            except Exception as e:
                logger.warning("Failed to capture query parameters: %s", e)
                query_params = "[Error capturing query parameters]"
        
        return {
            'headers': headers,
            'body': body,
            'query_params': query_params,
            'content_type': request.content_type if hasattr(request, 'content_type') else None,
        }
    
    def _capture_response_data(self, response):
        """
        Capture relevant data from the response.
        """
        headers = {}
        for key, value in response.items():
            headers[key.lower()] = value
        
        # Get response body if enabled
        body = None
        if self.log_response_body:
            try:
                # For streaming responses, we can't capture the body
                if hasattr(response, 'streaming') and response.streaming:
                    body = "[Streaming response]"
                elif hasattr(response, 'content'):
                    if isinstance(response.content, bytes):
                        body = response.content.decode('utf-8', errors='replace')
                    else:
                        body = str(response.content)
                    
                    # Truncate if too long
                    if len(body) > self.max_body_length:
                        body = body[:self.max_body_length] + '... [truncated]'
            except Exception as e:
                logger.warning("Failed to capture response body: %s", e)
                body = "[Error capturing response body]"
        
        return {
            'headers': headers,
            'body': body,
        }
    
    def _create_log_entry(self, request, request_data, response_data, status_code, response_time):
        """
        Create a log entry in the database.
        """
        # Get user ID
        user_id = None
        try:
            user_id = self.get_user_id(request)
        except Exception as e:
            logger.warning("Failed to get user ID: %s", e)
        
        # Get extra data if callable is provided
        extra_data = {}
        if self.get_extra_data:
            try:
                extra_data = self.get_extra_data(request, response_data)
            except Exception as e:
                logger.warning("Failed to get extra data: %s", e)
        
        # Get session ID if available
        session_id = None
        if hasattr(request, 'session') and hasattr(request.session, 'session_key'):
            session_id = request.session.session_key
        
        # Create the log entry
        RequestLog.objects.create(
            method=request.method,
            path=request.path,
            query_params=request_data['query_params'],
            headers=request_data['headers'],
            body=request_data['body'],
            content_type=request_data['content_type'],
            status_code=status_code,
            response_headers=response_data['headers'],
            response_body=response_data['body'],
            response_time_ms=response_time,
            ip_address=get_client_ip(request),
            user_id=user_id,
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            session_id=session_id,
            extra_data=extra_data,
        )
