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

## Production Deployment

### Gunicorn Configuration

The package provides a custom Gunicorn logger that logs requests to both a rotating file and the database. Configure it using these environment variables:

```bash
# Basic Gunicorn configuration
GUNICORN_BIND='0.0.0.0:8000'  # Address and port to bind to
GUNICORN_WORKERS=4            # Number of worker processes
GUNICORN_LOG_LEVEL='info'     # Logging level (debug, info, warning, error, critical)
GUNICORN_ACCESS_LOG='-'       # Path for access logs ('-' for stdout)
GUNICORN_ERROR_LOG='-'        # Path for error logs ('-' for stderr)
GUNICORN_MAX_REQUESTS=1000    # Maximum requests before worker restart
GUNICORN_MAX_REQUESTS_JITTER=50  # Random jitter to avoid all workers restarting at once

# File rotation configuration
GUNICORN_LOG_DIR='/var/log/gunicorn'  # Directory for log files
GUNICORN_LOG_MAX_BYTES=10485760       # Maximum log file size (10MB default)
GUNICORN_LOG_BACKUP_COUNT=10          # Number of backup files to keep
```

### Database Considerations

- The GunicornLogModel has a 120-day retention policy by default
- For high-traffic sites, consider database partitioning by date
- Ensure your database is properly sized to handle the log volume
- Consider setting up database maintenance tasks to optimize log tables

## Usage

Once installed and configured, the middleware will automatically log all requests and responses according to your settings.

### Accessing Logs

You can access the logs through the Django admin interface or directly via the `RequestLog` and `GunicornLogModel` models:

```python
from django_audit_logger.models import RequestLog, GunicornLogModel

# Get all Django request logs
logs = RequestLog.objects.all()

# Filter logs by path
api_logs = RequestLog.objects.filter(path__startswith='/api/')

# Filter logs by status code
error_logs = RequestLog.objects.filter(status_code__gte=400)

# Filter logs by user
user_logs = RequestLog.objects.filter(user_id='user123')

# Get all Gunicorn access logs
gunicorn_logs = GunicornLogModel.objects.all()

# Filter Gunicorn logs by URL
api_gunicorn_logs = GunicornLogModel.objects.filter(url__startswith='/api/')

# Filter Gunicorn logs by response code
error_gunicorn_logs = GunicornLogModel.objects.filter(code__gte=400)

# Filter Gunicorn logs by user
user_gunicorn_logs = GunicornLogModel.objects.filter(user_id='user123')
```

### Gunicorn Configuration

To use the included Gunicorn configuration with database logging:

1. Copy the `gunicorn_config.py` file to your project:
   ```bash
   cp /path/to/django_audit_logger/gunicorn_config.py /path/to/your/project/
   ```

2. Start Gunicorn with the config:
   ```bash
   gunicorn your_project.wsgi:application -c gunicorn_config.py
   ```

The Gunicorn configuration includes a custom logger class (`GLogger`) that logs all requests and responses to both files and the database via the `GunicornLogModel`.

## Log Maintenance

The package includes a management command for cleaning up old logs:

```bash
# Delete all logs older than 90 days (default)
python manage.py cleanup_audit_logs

# Delete logs older than 30 days
python manage.py cleanup_audit_logs --days=30

# Dry run (show what would be deleted without actually deleting)
python manage.py cleanup_audit_logs --dry-run

# Control batch size for large deletions
python manage.py cleanup_audit_logs --batch-size=5000

# Clean up only request logs
python manage.py cleanup_audit_logs --log-type=request

# Clean up only Gunicorn logs
python manage.py cleanup_audit_logs --log-type=gunicorn
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

3. **Log Directory Permissions**
   - Ensure the Gunicorn process has write permissions to the log directory
   - If using Docker, make sure the log volume is properly mounted

4. **Log Rotation Issues**
   - Check file permissions for log directory
   - Verify log rotation configuration in gunicorn_config.py

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
