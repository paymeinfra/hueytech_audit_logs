"""
Middleware for logging requests and responses to the database.
"""
import json
import time
import logging
from typing import Any, Dict, Optional, Callable, Union

from .models import RequestLog
from .utils import get_client_ip, mask_sensitive_data

logger = logging.getLogger('django_audit_logger')


class RequestLogMiddleware:
    """
    Middleware that logs all requests and responses to the database.
    """
    
    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response
        self.enabled = True
        self.log_request_body = True
        self.log_response_body = True
        self.max_body_length = 10000
        self.sensitive_fields = ['password', 'token', 'access', 'refresh']
        self.excluded_paths = ['/health', '/ping', '/favicon.ico']
        self.excluded_extensions = ['.css', '.js', '.jpg', '.jpeg', '.png', '.gif', '.ico']
        self.get_user_id = self._get_user_id
        self.get_extra_data = None
    
    def _should_skip_logging(self, request: Any) -> bool:
        """
        Determine if logging should be skipped for this request.
        """
        # Skip if path is in excluded paths
        if request.path in self.excluded_paths:
            return True
        
        # Skip if path ends with excluded extension
        for ext in self.excluded_extensions:
            if request.path.endswith(ext):
                return True
        
        return False
    
    def _get_user_id(self, request: Any) -> Optional[str]:
        """
        Get the user ID from the request.
        """
        if hasattr(request, 'user') and hasattr(request.user, 'id'):
            return str(request.user.id)
        return None
    
    def __call__(self, request: Any) -> Any:
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
        except (ValueError, TypeError, AttributeError, KeyError) as e:
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
            except (ValueError, TypeError, AttributeError, KeyError, json.JSONDecodeError) as e:
                # Log the error but don't disrupt the request/response cycle
                logger.exception("Failed to create audit log entry: %s", e)
        
        return response
    
    def _capture_request_data(self, request: Any) -> Dict[str, Any]:
        """
        Capture relevant data from the request.
        """
        headers = {}
        for key, value in request.META.items():
            if key.startswith('HTTP_'):
                header_name = key[5:].lower().replace('_', '-')
                headers[header_name] = value
            elif key in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
                header_name = key.lower().replace('_', '-')
                headers[header_name] = value
        
        # Get request body if enabled
        body = None
        if self.log_request_body and hasattr(request, 'body'):
            try:
                if isinstance(request.body, bytes):
                    body = request.body.decode('utf-8', errors='replace')
                else:
                    body = str(request.body)
                
                # Mask sensitive data
                body = mask_sensitive_data(body, self.sensitive_fields)
                
                # Truncate if too long
                if len(body) > self.max_body_length:
                    body = body[:self.max_body_length] + '... [truncated]'
            except (UnicodeDecodeError, ValueError, TypeError, AttributeError, json.JSONDecodeError) as e:
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
            except (ValueError, TypeError, json.JSONDecodeError) as e:
                logger.warning("Failed to capture query parameters: %s", e)
                query_params = "[Error capturing query parameters]"
        
        return {
            'headers': headers,
            'body': body,
            'query_params': query_params,
            'content_type': request.content_type if hasattr(request, 'content_type') else None,
        }
    
    def _capture_response_data(self, response: Any) -> Dict[str, Any]:
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
            except (UnicodeDecodeError, ValueError, TypeError, AttributeError) as e:
                logger.warning("Failed to capture response body: %s", e)
                body = "[Error capturing response body]"
        
        return {
            'headers': headers,
            'body': body,
        }
    
    def _create_log_entry(self, request: Any, request_data: Dict[str, Any], response_data: Dict[str, Any], status_code: int, response_time: int) -> None:
        """
        Create a log entry in the database.
        """
        # Get user ID
        user_id = None
        try:
            user_id = self.get_user_id(request)
        except (ValueError, TypeError, AttributeError) as e:
            logger.warning("Failed to get user ID: %s", e)
        
        # Get extra data if callable is provided
        extra_data = {}
        if self.get_extra_data:
            try:
                extra_data = self.get_extra_data(request, response_data)
            except (ValueError, TypeError, AttributeError) as e:
                logger.warning("Failed to get extra data: %s", e)
        
        # Get session ID if available
        session_id = None
        if hasattr(request, 'session') and hasattr(request.session, 'session_key'):
            session_id = request.session.session_key
        
        # Create the log entry
        try:
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
        except (ValueError, TypeError, AttributeError, KeyError) as e:
            logger.warning("Failed to create RequestLog object: %s", e)
