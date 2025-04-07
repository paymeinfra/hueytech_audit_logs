"""
Middleware for logging requests and responses to the database.
"""
import json
import time
import logging
from typing import Any, Dict, Callable

from .models import RequestLog
from .utils import get_client_ip, mask_sensitive_data
from .email_utils import capture_exception_and_notify

logger = logging.getLogger('django_audit_logger')


class RequestLogMiddleware:
    """
    Middleware for logging requests and responses to the database.
    """

    def __init__(self, get_response: Callable) -> None:
        """
        Initialize the middleware.
        
        Args:
            get_response: The next middleware or view in the chain
        """
        self.get_response = get_response
        self.sensitive_fields = getattr(
            self.get_response, 'sensitive_fields',
            ['password', 'token', 'access', 'refresh', 'secret', 'passwd', 'authorization', 'api_key']
        )
        self.exclude_paths = getattr(
            self.get_response, 'exclude_paths',
            ['/admin/jsi18n/', '/static/', '/media/']
        )
        self.exclude_extensions = getattr(
            self.get_response, 'exclude_extensions',
            ['.css', '.js', '.ico', '.jpg', '.png', '.gif', '.svg']
        )
        self.max_body_length = getattr(
            self.get_response, 'max_body_length',
            8192
        )

    @capture_exception_and_notify
    def __call__(self, request: Any) -> Any:
        """
        Process the request and response.
        
        Args:
            request: The Django request object
            
        Returns:
            The Django response object
        """
        # Skip logging for excluded paths
        path = request.path
        
        if any(path.startswith(prefix) for prefix in self.exclude_paths):
            return self.get_response(request)
            
        if any(path.endswith(ext) for ext in self.exclude_extensions):
            return self.get_response(request)
            
        # Start timer
        start_time = time.time()
        
        # Process request
        request_data = self._capture_request_data(request)
        
        # Get response
        response = self.get_response(request)
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Process response
        response_data = self._capture_response_data(response)
        
        # Create log entry
        self._create_log_entry(request, request_data, response, response_data, execution_time)
        
        return response

    @capture_exception_and_notify
    def _capture_request_data(self, request: Any) -> Dict[str, Any]:
        """
        Capture data from the request.
        
        Args:
            request: The Django request object
            
        Returns:
            dict: Request data
        """
        request_data = {
            'method': request.method,
            'path': request.path,
            'query_params': request.GET.dict(),
            'headers': dict(request.headers.items()),
            'client_ip': get_client_ip(request),
        }
        
        # Mask sensitive headers
        if 'headers' in request_data and request_data['headers']:
            for field in self.sensitive_fields:
                if field.lower() in request_data['headers']:
                    request_data['headers'][field.lower()] = '********'
        
        # Get request body
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                if request.content_type == 'application/json':
                    # Handle JSON request body
                    try:
                        body = json.loads(request.body.decode('utf-8'))
                        # Mask sensitive data
                        body_str = json.dumps(body)
                        masked_body = mask_sensitive_data(body_str, self.sensitive_fields)
                        request_data['body'] = masked_body
                    except (ValueError, TypeError, json.JSONDecodeError) as e:
                        logger.warning("Failed to parse JSON request body: %s", e)
                        # Try to mask sensitive data in raw body
                        body_str = request.body.decode('utf-8', errors='replace')
                        request_data['body'] = mask_sensitive_data(body_str, self.sensitive_fields)
                else:
                    # Handle form data
                    request_data['body'] = mask_sensitive_data(
                        str(request.POST.dict()), 
                        self.sensitive_fields
                    )
            except (ValueError, TypeError, AttributeError, KeyError) as e:
                logger.warning("Failed to capture request body: %s", e)
        
        # Truncate body if needed
        if 'body' in request_data and isinstance(request_data['body'], str):
            if len(request_data['body']) > self.max_body_length:
                request_data['body'] = request_data['body'][:self.max_body_length] + '... [truncated]'
        
        return request_data

    @capture_exception_and_notify
    def _capture_response_data(self, response: Any) -> Dict[str, Any]:
        """
        Capture data from the response.
        
        Args:
            response: The Django response object
            
        Returns:
            dict: Response data
        """
        response_data = {
            'status_code': response.status_code,
            'headers': dict(response.items()),
        }
        
        # Mask sensitive headers
        if 'headers' in response_data and response_data['headers']:
            for field in self.sensitive_fields:
                if field.lower() in response_data['headers']:
                    response_data['headers'][field.lower()] = '********'
        
        # Get response content
        if hasattr(response, 'content'):
            try:
                content = response.content.decode('utf-8', errors='replace')
                
                # Try to parse as JSON
                try:
                    json_content = json.loads(content)
                    # Mask sensitive data
                    content_str = json.dumps(json_content)
                    masked_content = mask_sensitive_data(content_str, self.sensitive_fields)
                    response_data['content'] = masked_content
                except (ValueError, TypeError, json.JSONDecodeError):
                    # Not JSON, use raw content
                    response_data['content'] = mask_sensitive_data(content, self.sensitive_fields)
                    
                # Truncate content if needed
                if len(response_data['content']) > self.max_body_length:
                    response_data['content'] = response_data['content'][:self.max_body_length] + '... [truncated]'
            except (ValueError, TypeError, AttributeError, KeyError) as e:
                logger.warning("Failed to capture response content: %s", e)
        
        return response_data

    @capture_exception_and_notify
    def _create_log_entry(self, request: Any, request_data: Dict[str, Any], 
                         response: Any, response_data: Dict[str, Any], 
                         execution_time: float) -> None:
        """
        Create a log entry in the database.
        
        Args:
            request: The Django request object
            request_data: Request data
            response: The Django response object (unused in base implementation, but may be used in subclasses)
            response_data: Response data
            execution_time: Execution time in seconds
        """
        # Get user ID if available
        user_id = None
        if hasattr(request, 'user') and hasattr(request.user, 'id'):
            user_id = request.user.id
        
        # Create log entry
        try:
            RequestLog.objects.create(
                method=request_data['method'],
                path=request_data['path'],
                query_params=json.dumps(request_data.get('query_params', {})),
                request_headers=json.dumps(request_data.get('headers', {})),
                request_body=request_data.get('body', ''),
                client_ip=request_data.get('client_ip', ''),
                user_id=user_id,
                status_code=response_data['status_code'],
                response_headers=json.dumps(response_data.get('headers', {})),
                response_body=response_data.get('content', ''),
                execution_time=execution_time
            )
        except (ValueError, TypeError, AttributeError, KeyError) as e:
            logger.error("Failed to create log entry: %s", e)
