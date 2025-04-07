"""
Admin interface for the Django Audit Logger package.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.template.defaultfilters import truncatechars
from .models import RequestLog


@admin.register(RequestLog)
class RequestLogAdmin(admin.ModelAdmin):
    """
    Admin interface for the RequestLog model.
    """
    list_display = (
        'timestamp', 'method', 'path_truncated', 'status_code', 
        'response_time_ms', 'user_id', 'ip_address'
    )
    list_filter = (
        'method', 'status_code', 'timestamp'
    )
    search_fields = (
        'path', 'user_id', 'ip_address', 'body', 'response_body'
    )
    readonly_fields = (
        'timestamp', 'method', 'path', 'query_params', 'headers',
        'body', 'content_type', 'status_code', 'response_headers',
        'response_body', 'response_time_ms', 'ip_address', 'user_id',
        'user_agent', 'session_id', 'extra_data', 'formatted_request_headers',
        'formatted_response_headers', 'formatted_extra_data'
    )
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Request Information', {
            'fields': (
                'timestamp', 'method', 'path', 'query_params', 
                'formatted_request_headers', 'body', 'content_type'
            ),
        }),
        ('Response Information', {
            'fields': (
                'status_code', 'response_time_ms', 'formatted_response_headers', 
                'response_body'
            ),
        }),
        ('User Information', {
            'fields': (
                'user_id', 'ip_address', 'user_agent', 'session_id'
            ),
        }),
        ('Additional Information', {
            'fields': (
                'formatted_extra_data',
            ),
        }),
    )
    
    def path_truncated(self, obj):
        """
        Truncate the path for display in the list view.
        """
        return truncatechars(obj.path, 50)
    path_truncated.short_description = 'Path'
    
    def formatted_request_headers(self, obj):
        """
        Format the request headers as HTML.
        """
        if not obj.headers:
            return "-"
        
        html = "<table>"
        for key, value in obj.headers.items():
            html += f"<tr><td><strong>{key}</strong></td><td>{value}</td></tr>"
        html += "</table>"
        return format_html(html)
    formatted_request_headers.short_description = 'Headers'
    
    def formatted_response_headers(self, obj):
        """
        Format the response headers as HTML.
        """
        if not obj.response_headers:
            return "-"
        
        html = "<table>"
        for key, value in obj.response_headers.items():
            html += f"<tr><td><strong>{key}</strong></td><td>{value}</td></tr>"
        html += "</table>"
        return format_html(html)
    formatted_response_headers.short_description = 'Response Headers'
    
    def formatted_extra_data(self, obj):
        """
        Format the extra data as HTML.
        """
        if not obj.extra_data:
            return "-"
        
        html = "<table>"
        for key, value in obj.extra_data.items():
            html += f"<tr><td><strong>{key}</strong></td><td>{value}</td></tr>"
        html += "</table>"
        return format_html(html)
    formatted_extra_data.short_description = 'Extra Data'
