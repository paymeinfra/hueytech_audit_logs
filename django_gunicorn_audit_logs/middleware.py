"""
Middleware for logging requests and responses to the database.
"""
import json
import time
import logging
from typing import Any, Dict, Callable

from django.conf import settings

from .models import RequestLog
from .utils import get_client_ip, mask_sensitive_data
from .email_utils import capture_exception_and_notify

logger = logging.getLogger('django_gunicorn_audit_logs')


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
        # Check if we should save the full body regardless of size
        self.save_full_body = getattr(
            settings, 'AUDIT_LOGS_SAVE_FULL_BODY', False
        )
        # Check if async logging is enabled
        self.use_async_logging = getattr(
            settings, 'AUDIT_LOGS_ASYNC_LOGGING', True
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
                        # Not JSON, use raw body
                        raw_body = request.body.decode('utf-8', errors='replace')
                        masked_body = mask_sensitive_data(raw_body, self.sensitive_fields)
                        request_data['body'] = masked_body
                else:
                    # Handle form data
                    try:
                        body = request.POST.dict()
                        # Mask sensitive data
                        for field in self.sensitive_fields:
                            if field in body:
                                body[field] = '********'
                        request_data['body'] = json.dumps(body)
                    except (ValueError, TypeError, AttributeError) as e:
                        # Fallback to raw body
                        raw_body = request.body.decode('utf-8', errors='replace')
                        masked_body = mask_sensitive_data(raw_body, self.sensitive_fields)
                        request_data['body'] = masked_body
            except (ValueError, TypeError, AttributeError, KeyError) as e:
                logger.warning("Failed to capture request body: %s", e)
        
        # Truncate body if needed
        if not self.save_full_body and 'body' in request_data and isinstance(request_data['body'], str):
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
                if not self.save_full_body and len(response_data['content']) > self.max_body_length:
                    response_data['content'] = response_data['content'][:self.max_body_length] + '... [truncated]'
            except (ValueError, TypeError, AttributeError, KeyError) as e:
                logger.warning("Failed to capture response content: %s", e)
        
        return response_data

    @capture_exception_and_notify
    def _create_log_entry(self, request: Any, request_data: Dict[str, Any], 
                     _: Any, response_data: Dict[str, Any], 
                     execution_time: float) -> None:
        """
        Create a log entry in the database.
        
        Args:
            request: The Django request object
            request_data: Request data
            _: The Django response object (unused in base implementation, but may be used in subclasses)
            response_data: Response data
            execution_time: Execution time in seconds
        """
        # Get user ID if available
        user_id = None
        if hasattr(request, 'user') and hasattr(request.user, 'id'):
            user_id = request.user.id
        
        # Create log entry
        try:
            if self.use_async_logging:
                try:
                    # Import here to avoid circular imports
                    from .tasks import create_request_log_entry, are_celery_workers_running
                    
                    # Only use Celery if workers are actually running
                    if are_celery_workers_running():
                        # Call the Celery task
                        create_request_log_entry.delay(
                            method=request_data['method'],
                            path=request_data['path'],
                            query_params=request_data.get('query_params', {}),
                            request_headers=request_data.get('headers', {}),
                            request_body=request_data.get('body', ''),
                            client_ip=request_data.get('client_ip', ''),
                            user_id=user_id,
                            status_code=response_data['status_code'],
                            response_headers=response_data.get('headers', {}),
                            response_body=response_data.get('content', ''),
                            execution_time=execution_time
                        )
                        logger.debug(f"Queued async log entry for {request_data['method']} {request_data['path']}")
                        return
                    else:
                        logger.debug("Celery workers not running, falling back to synchronous logging")
                except (ImportError, AttributeError) as e:
                    logger.warning(f"Failed to use Celery for async logging: {e}. Falling back to synchronous logging")
            
            # Create log entry synchronously (either by choice or as fallback)
            from .models import RequestLog
            
            # Check storage configuration
            use_mongo = getattr(settings, 'AUDIT_LOGS_USE_MONGO', False)
            write_to_both = getattr(settings, 'AUDIT_LOGS_WRITE_TO_BOTH', False)
            
            # Prepare log data
            query_params = json.dumps(request_data.get('query_params', {})) if isinstance(request_data.get('query_params'), dict) else request_data.get('query_params', '{}')
            request_headers = json.dumps(request_data.get('headers', {})) if isinstance(request_data.get('headers'), dict) else request_data.get('headers', '{}')
            response_headers = json.dumps(response_data.get('headers', {})) if isinstance(response_data.get('headers'), dict) else response_data.get('headers', '{}')
            
            log_data = {
                'method': request_data['method'],
                'path': request_data['path'],
                'query_params': query_params,
                'headers': request_headers,
                'body': request_data.get('body', ''),
                'ip_address': request_data.get('client_ip', ''),
                'user_id': user_id,
                'status_code': response_data['status_code'],
                'response_headers': response_headers,
                'response_body': response_data.get('content', ''),
                'response_time_ms': int(execution_time * 1000) if execution_time else None
            }
            
            # MongoDB storage logic if configured
            mongo_success = False
            if (use_mongo or write_to_both):
                try:
                    from .mongo_storage import mongo_storage
                    if mongo_storage.is_available():
                        # The create_request_log method now always returns a boolean
                        mongo_success = mongo_storage.create_request_log(**log_data)
                        if mongo_success:
                            logger.debug(f"Successfully created MongoDB log entry for {request_data['method']} {request_data['path']}")
                        else:
                            logger.warning(f"Failed to create MongoDB log entry for {request_data['method']} {request_data['path']}")
                except ImportError:
                    logger.warning("MongoDB storage not available")
            
            # PostgreSQL storage logic
            if not use_mongo or write_to_both or (use_mongo and not mongo_success):
                RequestLog.objects.create(**log_data)
                logger.debug(f"Created sync log entry for {request_data['method']} {request_data['path']}")
                
        except (ValueError, TypeError, AttributeError, KeyError) as e:
            logger.error("Failed to create log entry: %s", e)
