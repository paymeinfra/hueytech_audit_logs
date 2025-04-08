"""
Utility functions for the Django Gunicorn Audit Logs package.
"""
import json
import re
import logging
from typing import Optional, Union, Dict, List, Any

logger = logging.getLogger(__name__)


def get_client_ip(request: Any) -> str:
    """
    Get the client IP address from the request.
    
    Args:
        request: The Django request object
        
    Returns:
        str: The client IP address
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Get the first IP in case of multiple proxies
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip


def get_user_id(request: Any) -> Optional[Union[int, str]]:
    """
    Get the user ID from the request.
    
    Args:
        request: The Django request object
        
    Returns:
        int or str: The user ID, or None if not authenticated
    """
    if hasattr(request, 'user') and hasattr(request.user, 'id'):
        return request.user.id
    return None


def mask_sensitive_data(data_str: str, sensitive_fields: Optional[List[str]] = None) -> str:
    """
    Mask sensitive data in a string (JSON or form data).
    
    Args:
        data_str (str): The data string to mask
        sensitive_fields (list): List of field names to mask
        
    Returns:
        str: The masked data string
    """
    if not data_str or not sensitive_fields:
        return data_str
    
    try:
        # Try to parse as JSON
        data = json.loads(data_str)
        is_json = True
    except (ValueError, TypeError, json.JSONDecodeError):
        # Not JSON, treat as form data
        data = data_str
        is_json = False
    
    if is_json:
        # Mask sensitive fields in JSON
        _mask_sensitive_json(data, sensitive_fields)
        return json.dumps(data)
    else:
        # Mask sensitive fields in form data
        for field in sensitive_fields:
            pattern = rf'({field}=)([^&]+)'
            data = re.sub(pattern, r'\1********', data)
        return data


def _mask_sensitive_json(data: Any, sensitive_fields: List[str], path: str = "") -> None:
    """
    Recursively mask sensitive fields in a JSON object.
    
    Args:
        data: The JSON object to mask
        sensitive_fields: List of field names to mask
        path: Current path in the JSON object (for nested objects)
    """
    if isinstance(data, dict):
        for key, value in list(data.items()):
            current_path = f"{path}.{key}" if path else key
            
            # Check if this key should be masked
            if key in sensitive_fields:
                data[key] = "********"
            elif isinstance(value, (dict, list)):
                _mask_sensitive_json(value, sensitive_fields, current_path)
    
    elif isinstance(data, list):
        for i, item in enumerate(data):
            current_path = f"{path}[{i}]"
            _mask_sensitive_json(item, sensitive_fields, current_path)


def truncate_data(data: str, max_length: int) -> str:
    """
    Truncate data to the specified maximum length.
    
    Args:
        data (str): The data to truncate
        max_length (int): Maximum length of the data
        
    Returns:
        str: Truncated data
    """
    if not data or not isinstance(data, str):
        return data
    
    if len(data) <= max_length:
        return data
    
    return data[:max_length] + '... [truncated]'
