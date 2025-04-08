"""
Database models for the Django Gunicorn Audit Logs package.
"""
import json
from typing import Dict, Any, Optional, Union
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property


class RequestLog(models.Model):
    """
    Model for storing HTTP request and response logs.
    """
    # Request information
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    method = models.CharField(max_length=10, db_index=True)
    path = models.TextField(db_index=True)
    query_params = models.TextField(null=True, blank=True)
    headers = models.JSONField(default=dict)
    body = models.TextField(null=True, blank=True)
    content_type = models.CharField(max_length=100, null=True, blank=True)
    
    # Response information
    status_code = models.IntegerField(db_index=True)
    response_headers = models.JSONField(default=dict)
    response_body = models.TextField(null=True, blank=True)
    response_time_ms = models.IntegerField(null=True, blank=True)
    
    # User information
    ip_address = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    user_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    user_agent = models.TextField(null=True, blank=True)
    session_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    
    # Additional data
    extra_data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name = "Request Log"
        verbose_name_plural = "Request Logs"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp', 'method']),
            models.Index(fields=['timestamp', 'status_code']),
            models.Index(fields=['timestamp', 'user_id']),
            models.Index(fields=['timestamp', 'ip_address']),
        ]
    
    def __str__(self) -> str:
        return f"{self.method} {self.path} - {self.status_code} ({self.timestamp.strftime('%Y-%m-%d %H:%M:%S')})"
    
    @cached_property
    def headers_dict(self) -> Dict[str, Any]:
        """
        Return headers as a dictionary.
        """
        if isinstance(self.headers, str):
            try:
                return json.loads(self.headers)
            except json.JSONDecodeError:
                return {}
        return self.headers
    
    @cached_property
    def response_headers_dict(self) -> Dict[str, Any]:
        """
        Return response headers as a dictionary.
        """
        if isinstance(self.response_headers, str):
            try:
                return json.loads(self.response_headers)
            except json.JSONDecodeError:
                return {}
        return self.response_headers
    
    @cached_property
    def extra_data_dict(self) -> Dict[str, Any]:
        """
        Return extra data as a dictionary.
        """
        if isinstance(self.extra_data, str):
            try:
                return json.loads(self.extra_data)
            except json.JSONDecodeError:
                return {}
        return self.extra_data


class GunicornLogModel(models.Model):
    """
    Model for storing Gunicorn access logs.
    """
    # Request information
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    method = models.CharField(
        max_length=20,  # Increased to safely accommodate all HTTP method names
        choices=[
            ('GET', 'GET'),
            ('POST', 'POST'),
            ('PUT', 'PUT'),
            ('DELETE', 'DELETE'),
            ('PATCH', 'PATCH'),
            ('OPTIONS', 'OPTIONS'),
            ('HEAD', 'HEAD'),
        ],
        db_index=True
    )
    url = models.TextField(db_index=True)
    host = models.CharField(max_length=255, db_index=True)
    
    # User information
    user_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    user_ip = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    agent = models.CharField(max_length=255, null=True, blank=True)
    source = models.CharField(max_length=255, null=True, blank=True)
    
    # Request and response data
    request = models.JSONField(default=dict)
    response = models.JSONField(default=dict)
    headers = models.JSONField(default=dict)
    
    # Performance metrics
    duration = models.IntegerField(null=True, blank=True)  # microseconds
    code = models.IntegerField(null=True, blank=True, db_index=True)
    
    class Meta:
        verbose_name = "Gunicorn Log"
        verbose_name_plural = "Gunicorn Logs"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp', 'method']),
            models.Index(fields=['timestamp', 'code']),
            models.Index(fields=['timestamp', 'user_id']),
            models.Index(fields=['timestamp', 'user_ip']),
        ]
    
    def __str__(self) -> str:
        return f"{self.method} {self.url} - {self.code} ({self.timestamp.strftime('%Y-%m-%d %H:%M:%S')})"
