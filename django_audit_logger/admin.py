"""
Admin interface for the Django Audit Logger package.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.template.defaultfilters import truncatechars
from .models import RequestLog, GunicornLogModel


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


@admin.register(GunicornLogModel)
class GunicornLogModelAdmin(admin.ModelAdmin):
    """
    Admin interface for the GunicornLogModel.
    """
    list_display = (
        'timestamp', 'method', 'url_truncated', 'code', 
        'duration', 'user_id', 'user_ip'
    )
    list_filter = (
        'method', 'code', 'timestamp'
    )
    search_fields = (
        'url', 'user_id', 'user_ip', 'host', 'agent'
    )
    readonly_fields = (
        'timestamp', 'method', 'url', 'host', 'user_id',
        'user_ip', 'agent', 'source', 'request', 'response',
        'headers', 'duration', 'code', 'formatted_request_data',
        'formatted_response_data', 'formatted_headers'
    )
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Request Information', {
            'fields': (
                'timestamp', 'method', 'url', 'host', 
                'formatted_headers', 'formatted_request_data'
            ),
        }),
        ('Response Information', {
            'fields': (
                'code', 'duration', 'formatted_response_data'
            ),
        }),
        ('User Information', {
            'fields': (
                'user_id', 'user_ip', 'agent', 'source'
            ),
        }),
    )
    
    def url_truncated(self, obj):
        """
        Truncate the URL for display in the list view.
        """
        return truncatechars(obj.url, 50)
    url_truncated.short_description = 'URL'
    
    def formatted_request_data(self, obj):
        """
        Format the request data as HTML.
        """
        if not obj.request:
            return "-"
        
        html = "<table>"
        for key, value in obj.request.items():
            html += f"<tr><td><strong>{key}</strong></td><td>{value}</td></tr>"
        html += "</table>"
        return format_html(html)
    formatted_request_data.short_description = 'Request Data'
    
    def formatted_response_data(self, obj):
        """
        Format the response data as HTML.
        """
        if not obj.response:
            return "-"
        
        html = "<table>"
        for key, value in obj.response.items():
            html += f"<tr><td><strong>{key}</strong></td><td>{value}</td></tr>"
        html += "</table>"
        return format_html(html)
    formatted_response_data.short_description = 'Response Data'
    
    def formatted_headers(self, obj):
        """
        Format the headers as HTML.
        """
        if not obj.headers:
            return "-"
        
        html = "<table>"
        for key, value in obj.headers.items():
            html += f"<tr><td><strong>{key}</strong></td><td>{value}</td></tr>"
        html += "</table>"
        return format_html(html)
    formatted_headers.short_description = 'Headers'
