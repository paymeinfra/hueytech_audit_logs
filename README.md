# Django Audit Logger

A production-grade Django package for comprehensive request/response logging with PostgreSQL storage and Gunicorn configuration.

## Package Structure

The `django-audit-logger` package includes:

1. **Core Middleware** for logging all HTTP requests and responses to PostgreSQL
2. **Database Models** with optimized indexes for efficient querying
3. **Admin Interface** for easy log viewing and filtering
4. **Gunicorn Configuration** with file logging and rotation
5. **Management Commands** for log maintenance
6. **Comprehensive Tests** to ensure reliability

## Key Features

- Detailed request/response logging with configurable options
- Sensitive data masking for security
- Configurable path exclusions to avoid logging static files
- Performance optimizations for production use
- Batch processing for cleanup operations
- Comprehensive error handling

## Installation

### From your organization's repository

```bash
pip install django-audit-logger --extra-index-url=https://your-org-repo-url/simple/
```

### Development installation

```bash
git clone https://github.com/yourorganization/django-audit-logger.git
cd django-audit-logger
pip install -e .
```

## Configuration

### Django Settings

Add the following to your Django settings:

```python
INSTALLED_APPS = [
    # ... other apps
    'django_audit_logger',
]

MIDDLEWARE = [
    # ... other middleware
    'django_audit_logger.middleware.AuditLogMiddleware',
]

# Audit Logger Settings
AUDIT_LOGGER = {
    'ENABLED': True,
    'LOG_REQUEST_BODY': True,
    'LOG_RESPONSE_BODY': True,
    'EXCLUDE_PATHS': ['/health/', '/metrics/'],
    'EXCLUDE_EXTENSIONS': ['.jpg', '.png', '.gif', '.css', '.js'],
    'MAX_BODY_LENGTH': 10000,  # Truncate bodies longer than this value
    'SENSITIVE_FIELDS': ['password', 'token', 'access_key', 'secret'],
    'USER_ID_CALLABLE': 'django_audit_logger.utils.get_user_id',
    'EXTRA_DATA_CALLABLE': None,  # Optional function to add custom data
}
```

### Database Configuration

The package requires a PostgreSQL database. Make sure your `DATABASES` setting includes a connection:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'your_database',
        'USER': 'your_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## Production Considerations

The package is designed with production use in mind:
- Efficient database queries with proper indexing
- Batched cleanup operations to prevent memory issues
- Configurable retention periods
- Error handling to prevent disruption of the request/response cycle

## Usage

Once installed and configured, the middleware will automatically log all requests and responses according to your settings.

### Accessing Logs

You can access the logs through the Django admin interface or directly via the `RequestLog` model:

```python
from django_audit_logger.models import RequestLog

# Get all logs
logs = RequestLog.objects.all()

# Filter logs by path
api_logs = RequestLog.objects.filter(path__startswith='/api/')

# Filter logs by status code
error_logs = RequestLog.objects.filter(status_code__gte=400)

# Filter logs by user
user_logs = RequestLog.objects.filter(user_id='user123')
```

### Gunicorn Configuration

To use the included Gunicorn configuration:

1. Copy the `gunicorn_config.py` file to your project:
   ```bash
   cp /path/to/django_audit_logger/gunicorn_config.py /path/to/your/project/
   ```

2. Start Gunicorn with the config:
   ```bash
   gunicorn your_project.wsgi:application -c gunicorn_config.py
   ```

## Log Maintenance

The package includes a management command for cleaning up old logs:

```bash
# Delete logs older than 90 days (default)
python manage.py cleanup_audit_logs

# Delete logs older than 30 days
python manage.py cleanup_audit_logs --days=30

# Dry run (show what would be deleted without actually deleting)
python manage.py cleanup_audit_logs --dry-run

# Control batch size for large deletions
python manage.py cleanup_audit_logs --batch-size=5000
```

## Customization

### Custom User ID Extraction

You can define a custom function to extract user IDs:

```python
# In your project's utils.py
def get_custom_user_id(request):
    if hasattr(request, 'user') and request.user.is_authenticated:
        return request.user.email  # Or any other identifier
    return None

# In settings.py
AUDIT_LOGGER = {
    # ... other settings
    'USER_ID_CALLABLE': 'path.to.your.utils.get_custom_user_id',
}
```

### Adding Custom Data

You can add custom data to each log entry:

```python
# In your project's utils.py
def get_extra_data(request, response):
    return {
        'tenant_id': getattr(request, 'tenant_id', None),
        'correlation_id': request.headers.get('X-Correlation-ID'),
        # Add any other custom data
    }

# In settings.py
AUDIT_LOGGER = {
    # ... other settings
    'EXTRA_DATA_CALLABLE': 'path.to.your.utils.get_extra_data',
}
```

## Performance Considerations

- For high-traffic sites, consider using a separate database for audit logs
- Use the `EXCLUDE_PATHS` and `EXCLUDE_EXTENSIONS` settings to avoid logging static files
- Set appropriate values for `MAX_BODY_LENGTH` to prevent storing excessive data
- Consider implementing a periodic cleanup job for old logs

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
   - Ensure PostgreSQL is running and accessible
   - Verify database credentials are correct

2. **Performance Impact**
   - If you notice performance degradation, try disabling request/response body logging
   - Increase the exclusion paths for high-traffic, low-value endpoints

3. **Log Rotation Issues**
   - Check file permissions for log directory
   - Verify log rotation configuration in gunicorn_config.py

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
