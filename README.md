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

### Error Email Notifications

The package includes an error notification system that sends emails via AWS SES when exceptions occur in the middleware or logging system. Configure it using these environment variables:

```bash
# AWS Credentials (required for SES email notifications)
AWS_ACCESS_KEY_ID='your-access-key'
AWS_SECRET_ACCESS_KEY='your-secret-key'
AWS_SES_REGION_NAME='us-east-1'  # AWS region for SES

# Email Configuration
AUDIT_LOGGER_ERROR_EMAIL_SENDER='alerts@yourdomain.com'
AUDIT_LOGGER_ERROR_EMAIL_RECIPIENTS='admin@yourdomain.com,devops@yourdomain.com'
AUDIT_LOGGER_RAISE_EXCEPTIONS='False'  # Set to 'True' to re-raise exceptions after logging
```

Make sure to add these variables to your `.env` file or environment configuration. The package uses python-dotenv to automatically load variables from a `.env` file.

### Database Considerations

- The GunicornLogModel has a 120-day retention policy by default
- For high-traffic sites, consider database partitioning by date
- Ensure your database is properly sized to handle the log volume
- Consider setting up database maintenance tasks to optimize log tables

### Database Router Configuration

The package includes a custom database router (`AuditLogRouter`) that directs all audit log operations to a dedicated database. This separation improves performance by keeping log writes from affecting your main application database.

To use the router, add the following to your Django settings:

```python
# settings.py

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'your_main_db',
        # ... other database settings
    },
    'audit_logs': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'audit_logs_db',
        'USER': os.environ.get('AUDIT_LOGS_DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('AUDIT_LOGS_DB_PASSWORD', ''),
        'HOST': os.environ.get('AUDIT_LOGS_DB_HOST', 'localhost'),
        'PORT': os.environ.get('AUDIT_LOGS_DB_PORT', '5432'),
    }
}

DATABASE_ROUTERS = ['django_audit_logger.routers.AuditLogRouter']
```

Make sure to create the `audit_logs_db` database before running migrations:

```bash
createdb audit_logs_db
python manage.py migrate django_audit_logger --database=audit_logs
```

For production environments, add the database credentials to your `.env` file:

```bash
AUDIT_LOGS_DB_NAME=audit_logs_db
AUDIT_LOGS_DB_USER=audit_user
AUDIT_LOGS_DB_PASSWORD=secure_password
AUDIT_LOGS_DB_HOST=your-db-host.example.com
AUDIT_LOGS_DB_PORT=5432
```

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

## Examples

The package includes several example files to help you get started:

### Settings Example

Check out `examples/settings_example.py` for a complete example of how to configure Django settings for the audit logger, including:

- Database router configuration
- Error email notification settings
- Logging configuration
- Environment variable integration

### Usage Examples

The `examples/usage_example.py` file demonstrates:

- How to use the `capture_exception_and_notify` decorator
- How to run migrations for the audit logs database
- How to check database connections
- Example API views that are automatically logged

### Custom Middleware Example

The `examples/custom_middleware_example.py` file shows how to extend the base middleware:

- Add custom fields to log entries
- Implement custom masking for sensitive data
- Add custom error handling and notifications

### Database Setup Script

The `examples/setup_audit_logs_db.py` script helps you set up a separate database for audit logs:

```bash
# Run the setup script
python examples/setup_audit_logs_db.py --project-path /path/to/your/project --db-name audit_logs_db
```

## Troubleshooting

### Common Issues

1. **Missing Dependencies**
   - Ensure boto3 is installed for email notifications: `pip install boto3`
   - Ensure python-dotenv is installed for environment variables: `pip install python-dotenv`

2. **Database Connection Issues**
   - Check database credentials in your .env file
   - Ensure the audit_logs database exists
   - Run migrations with: `python manage.py migrate django_audit_logger --database=audit_logs`

3. **Email Notification Issues**
   - Verify AWS credentials are correctly set
   - Check that SES is configured in your AWS account
   - Ensure sender email is verified in SES

4. **Performance Issues**
   - Consider increasing the `AUDIT_LOGGER_MAX_BODY_LENGTH` setting
   - Exclude more paths in `AUDIT_LOGGER_EXCLUDE_PATHS`
   - Set up regular database maintenance for the audit logs table

### Getting Help

If you encounter issues not covered in this documentation, please open an issue on the GitHub repository.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
