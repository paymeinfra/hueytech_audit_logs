"""
Example of a custom middleware that extends the Django Audit Logger middleware.
"""
import json
import logging
from typing import Any, Dict, Optional

from django_audit_logger.middleware import AuditLogMiddleware
from django_audit_logger.email_utils import capture_exception_and_notify

logger = logging.getLogger('django_audit_logger')


class CustomAuditLogMiddleware(AuditLogMiddleware):
    """
    Custom middleware that extends the base AuditLogMiddleware to add additional functionality.
    
    This example shows how to:
    1. Add custom fields to the log entry
    2. Implement custom masking for sensitive data
    3. Add custom error handling and notifications
    """
    
    def __init__(self, get_response):
        """Initialize the middleware."""
        super().__init__(get_response)
        # Add any additional initialization here
        self.sensitive_fields.extend([
            'ssn',
            'tax_id',
            'account_number',
            'routing_number',
        ])
    
    @capture_exception_and_notify
    def _get_request_data(self, request: Any) -> Dict[str, Any]:
        """
        Override to add custom request data extraction.
        
        Args:
            request: The Django request object
            
        Returns:
            Dict containing request data
        """
        # Get base request data from parent class
        request_data = super()._get_request_data(request)
        
        # Add custom fields
        request_data['is_api_request'] = request.path.startswith('/api/')
        request_data['is_authenticated'] = hasattr(request, 'user') and getattr(request.user, 'is_authenticated', False)
        
        # Add custom headers you want to track
        if 'headers' in request_data:
            headers = request_data['headers']
            request_data['api_version'] = headers.get('X-API-Version', '')
            request_data['client_version'] = headers.get('X-Client-Version', '')
        
        return request_data
    
    @capture_exception_and_notify
    def _get_response_data(self, response: Any) -> Dict[str, Any]:
        """
        Override to add custom response data extraction.
        
        Args:
            response: The Django response object
            
        Returns:
            Dict containing response data
        """
        # Get base response data from parent class
        response_data = super()._get_response_data(response)
        
        # Add custom processing for specific response types
        if hasattr(response, 'status_code') and response.status_code >= 400:
            # For error responses, try to extract error details
            try:
                if 'content' in response_data and response_data['content']:
                    content = json.loads(response_data['content'])
                    if isinstance(content, dict) and 'error' in content:
                        response_data['error_message'] = content['error']
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
        
        return response_data
    
    @capture_exception_and_notify
    def _create_log_entry(self, request: Any, request_data: Dict[str, Any], 
                         response: Any, response_data: Dict[str, Any], 
                         execution_time: float) -> None:
        """
        Override to customize log entry creation.
        
        Args:
            request: The Django request object
            request_data: Request data
            response: The Django response object
            response_data: Response data
            execution_time: Execution time in seconds
        """
        # Add custom logging before creating the log entry
        if hasattr(response, 'status_code') and response.status_code >= 500:
            logger.error(
                "Server error occurred: %s %s (status: %s, time: %.2fms)",
                request_data.get('method', ''),
                request_data.get('path', ''),
                response_data.get('status_code', ''),
                execution_time * 1000
            )
        
        # Call parent method to create the log entry
        super()._create_log_entry(request, request_data, response, response_data, execution_time)
        
        # Add custom post-processing if needed
        if hasattr(request, 'user') and getattr(request.user, 'is_authenticated', False):
            # Example: Update user's last activity timestamp
            # user_profile = request.user.profile
            # user_profile.last_activity = timezone.now()
            # user_profile.save()
            pass
