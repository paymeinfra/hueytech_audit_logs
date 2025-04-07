# Django Audit Logger

A production-grade Django package for comprehensive request/response logging with PostgreSQL storage and Gunicorn configuration.

## Package Structure

The `django_audit_logger` package includes:

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
pip install django_audit_logger --extra-index-url=https://your-org-repo-url/simple/
```

### Development installation

```bash
git clone https://github.com/paymeinfra/hueytech_audit_logs.git
cd hueytech_audit_logs
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
    'django_audit_logger.middleware.RequestLogMiddleware',
]

# Audit Logger Settings
AUDIT_LOGS = {
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

# Enable asynchronous logging with Celery (optional)
AUDIT_LOGS_ASYNC_LOGGING = True
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
AUDIT_LOGS_ERROR_EMAIL_SENDER='alerts@yourdomain.com'
AUDIT_LOGS_ERROR_EMAIL_RECIPIENTS='admin@yourdomain.com,devops@yourdomain.com'
AUDIT_LOGS_RAISE_EXCEPTIONS='False'  # Set to 'True' to re-raise exceptions after logging
```

## Environment Variables

Django Audit Logger can be configured using environment variables. Here's a list of available environment variables:

### Database Configuration

```
# PostgreSQL Database Configuration
AUDIT_LOGS_DB_NAME=audit_logs_db
AUDIT_LOGS_DB_USER=audit_user
AUDIT_LOGS_DB_PASSWORD=secure_password
AUDIT_LOGS_DB_HOST=localhost
AUDIT_LOGS_DB_PORT=5432

# MongoDB Configuration
AUDIT_LOGS_USE_MONGO=False
AUDIT_LOGS_WRITE_TO_BOTH=False
AUDIT_LOGS_MONGO_URI=mongodb+srv://username:password@cluster0.example.mongodb.net/
AUDIT_LOGS_MONGO_DB_NAME=audit_logs
AUDIT_LOGS_MONGO_REQUEST_LOGS_COLLECTION=request_logs
AUDIT_LOGS_MONGO_GUNICORN_LOGS_COLLECTION=gunicorn_logs
```

### Gunicorn Configuration

```
# Gunicorn Server Settings
GUNICORN_BIND=0.0.0.0:8000
GUNICORN_WORKERS=4
GUNICORN_LOG_LEVEL=info
GUNICORN_ACCESS_LOG=-
GUNICORN_ERROR_LOG=-
GUNICORN_MAX_REQUESTS=1000
GUNICORN_MAX_REQUESTS_JITTER=50

# File Rotation Configuration
GUNICORN_LOG_DIR=/var/log/gunicorn
GUNICORN_LOG_MAX_BYTES=10485760
GUNICORN_LOG_BACKUP_COUNT=10
```

### AWS and Email Configuration

```
# AWS Credentials for SES Email Notifications
AUDIT_LOGS_AWS_ACCESS_KEY_ID=your-aws-access-key
AUDIT_LOGS_AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AUDIT_LOGS_AWS_SES_REGION_NAME=us-east-1

# Email Notification Settings
AUDIT_LOGGER_ERROR_EMAIL_SENDER=alerts@yourdomain.com
AUDIT_LOGGER_ERROR_EMAIL_RECIPIENTS=admin@yourdomain.com,devops@yourdomain.com
AUDIT_LOGGER_RAISE_EXCEPTIONS=False
```

### Other Settings

```
# Audit Logger Settings
AUDIT_LOGGER_MAX_BODY_LENGTH=8192

# Async Logging Configuration
AUDIT_LOGS_ASYNC_LOGGING=False
```

### Celery Queue Configuration

```
AUDIT_CELERY_QUEUE=audit_logs
```

See the `.env.example` file for a complete example of all available environment variables.

## Database Router Configuration

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

## Asynchronous Logging with Celery

Django Audit Logger supports asynchronous database logging using Celery tasks. This can significantly improve performance by moving database write operations to background tasks, especially in high-traffic environments.

### Installation

Install the package with Celery support:

```bash
pip install django-audit-logger[async]
```

### Configuration

1. Configure Celery in your Django project as per the [Celery documentation](https://docs.celeryproject.org/en/stable/django/first-steps-with-django.html).

2. Enable asynchronous logging in your settings:

```python
# Enable asynchronous logging with Celery
AUDIT_LOGS_ASYNC_LOGGING = True
```

### Benefits

- Reduced request processing time
- Improved application responsiveness
- Better handling of logging spikes during high traffic
- Fault tolerance with automatic retries for failed log entries

### Retry Mechanism

The asynchronous logging system includes a robust retry mechanism for handling failures:

- **Automatic Retries**: Failed logging tasks are automatically retried up to 3 times
- **Exponential Backoff**: 60-second delay between retries with exponential backoff
- **Error Logging**: All retry attempts are logged for monitoring
- **Exception Handling**: Handles database unavailability, network issues, and resource constraints

You can customize the retry behavior in your Django settings:

```python
# Celery task retry settings for audit logging
CELERY_TASK_ROUTES = {
    'django_audit_logger.tasks.create_request_log_entry': {
        'queue': 'audit_logs'
    }
}

CELERY_TASK_ACKS_LATE = True  # Ensure tasks aren't acknowledged until completed
```

### Scaling for High-Volume Applications

For extremely high-volume applications (millions to billions of requests), consider these additional configurations:

1. **Database Partitioning**:
   ```sql
   -- Example PostgreSQL partitioning by month
   CREATE TABLE audit_logs_partitioned (
       LIKE django_audit_logger_requestlog INCLUDING ALL
   ) PARTITION BY RANGE (timestamp);
   
   -- Create monthly partitions
   CREATE TABLE audit_logs_y2025m04 PARTITION OF audit_logs_partitioned
   FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');
   ```

2. **Worker Scaling**:
   ```bash
   # Run multiple Celery workers
   celery -A your_project worker -Q audit_logs --concurrency=8 -n audit_worker1@%h
   celery -A your_project worker -Q audit_logs --concurrency=8 -n audit_worker2@%h
   ```

3. **Request Sampling** (add to your settings):
   ```python
   # Only log 10% of successful GET requests
   AUDIT_LOGS = {
       # ... other settings
       'SAMPLING_RATES': {
           'GET': {200: 0.1, 'default': 1.0},  # Log 10% of 200 GET responses, 100% of others
           'default': 1.0  # Log all other methods
       }
   }
   ```

### Considerations

- Requires a running Celery worker
- Logs might be slightly delayed in appearing in the database
- Memory usage may increase if there's a large backlog of tasks
- For billions of requests, implement database partitioning and log rotation

If Celery is not available or `AUDIT_LOGS_ASYNC_LOGGING` is set to `False`, the middleware will fall back to synchronous logging.

### Usage

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

## MongoDB Support for High-Volume Logging

For extremely high-volume applications handling billions of requests, Django Audit Logger now supports MongoDB as an alternative storage backend. MongoDB provides better scaling capabilities for write-heavy workloads compared to traditional relational databases.

### Installation

Install the package with MongoDB support:

```bash
pip install django-audit-logger[mongo]
```

### Configuration

Add MongoDB connection settings to your Django settings:

```python
# MongoDB configuration for audit logs
AUDIT_LOGS_USE_MONGO = True
AUDIT_LOGS_MONGO = {
    'URI': 'mongodb://username:password@10.0.0.1:27017,10.0.0.2:27017,10.0.0.3:27017/?replicaSet=rs0&authSource=admin',
    'DB_NAME': 'audit_logs',
    'REQUEST_LOGS_COLLECTION': 'request_logs',
    'GUNICORN_LOGS_COLLECTION': 'gunicorn_logs'
}
```

#### Connecting to Different MongoDB Deployments

The package supports various MongoDB deployment types:

1. **Self-Managed MongoDB Cluster**:
   ```
   AUDIT_LOGS_MONGO_URI=mongodb://username:password@10.0.0.1:27017,10.0.0.2:27017,10.0.0.3:27017/?replicaSet=rs0&authSource=admin
   ```

2. **MongoDB Atlas (Cloud)**:
   ```
   AUDIT_LOGS_MONGO_URI=mongodb+srv://username:password@cluster0.example.mongodb.net/
   ```

3. **Single MongoDB Instance**:
   ```
   AUDIT_LOGS_MONGO_URI=mongodb://username:password@localhost:27017/
   ```

The connection string supports all standard MongoDB connection options, including:
- Replica set configuration
- Authentication mechanisms
- SSL/TLS options
- Connection pool settings
- Read preference and write concern

### Benefits of MongoDB Storage

- **Horizontal Scaling**: MongoDB can be easily scaled across multiple servers in a sharded cluster
- **Schema Flexibility**: No migrations needed when log structure changes
- **High Write Throughput**: Optimized for high-volume write operations
- **Automatic Sharding**: Distributes data across multiple machines
- **Document-Oriented**: Better suited for storing JSON-like log data

### Fallback Mechanism

If MongoDB is enabled but unavailable, the system will automatically fall back to PostgreSQL storage. This ensures your logs are always captured, even during MongoDB maintenance or outages.

### Query Examples

```python
# Import the MongoDB storage backend
from django_audit_logger.mongo_storage import mongo_storage

# Get recent error logs
error_logs = mongo_storage.get_request_logs(
    status_code=500,
    limit=100
)

# Get logs for a specific user
user_logs = mongo_storage.get_request_logs(
    user_id='user123',
    limit=50
)

# Clean up old logs
deleted_count = mongo_storage.cleanup_old_logs(days=90)
```

## Dual Storage: PostgreSQL and MongoDB

For critical applications that require both the relational capabilities of PostgreSQL and the scaling advantages of MongoDB, Django Audit Logger supports writing logs to both databases simultaneously.

### Configuration

Enable dual storage by adding the following to your Django settings:

```python
# Enable writing to both PostgreSQL and MongoDB
AUDIT_LOGS_USE_MONGO = True  # MongoDB must be enabled
AUDIT_LOGS_WRITE_TO_BOTH = True  # Write to both databases
```

### Benefits of Dual Storage

- **Data Redundancy**: Critical logs are stored in two separate database systems
- **Flexible Querying**: Use SQL for complex relational queries and MongoDB for high-volume analytics
- **Migration Path**: Gradually transition from PostgreSQL to MongoDB while maintaining data integrity
- **Performance Optimization**: Use PostgreSQL for transactional integrity and MongoDB for high-throughput logging

### Performance Considerations

When dual storage is enabled, the system attempts to write to MongoDB first. If the MongoDB write succeeds, it proceeds to write to PostgreSQL. This approach ensures that the faster MongoDB write doesn't have to wait for the PostgreSQL write to complete.

If MongoDB is temporarily unavailable, the system will still write to PostgreSQL, ensuring no data loss occurs during MongoDB outages.

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
   - Consider increasing the `AUDIT_LOGS_MAX_BODY_LENGTH` setting
   - Exclude more paths in `AUDIT_LOGS_EXCLUDE_PATHS`
   - Set up regular database maintenance for the audit logs table

### Getting Help

If you encounter issues not covered in this documentation, please open an issue on the GitHub repository.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Environment Variables

The Django Audit Logger can be configured using the following environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| AUDIT_LOGS_DB_NAME | PostgreSQL database name | audit_logs_db |
| AUDIT_LOGS_DB_USER | PostgreSQL database user | audit_user |
| AUDIT_LOGS_DB_PASSWORD | PostgreSQL database password | secure_password |
| AUDIT_LOGS_DB_HOST | PostgreSQL database host | localhost |
| AUDIT_LOGS_DB_PORT | PostgreSQL database port | 5432 |
| AUDIT_LOGS_USE_MONGO | Use MongoDB for storage | False |
| AUDIT_LOGS_WRITE_TO_BOTH | Write to both PostgreSQL and MongoDB | False |
| AUDIT_LOGS_MONGO_URI | MongoDB connection URI | mongodb://localhost:27017/ |
| AUDIT_LOGS_MONGO_DB_NAME | MongoDB database name | audit_logs |
| AUDIT_LOGS_MONGO_REQUEST_LOGS_COLLECTION | MongoDB collection for request logs | request_logs |
| AUDIT_LOGS_MONGO_GUNICORN_LOGS_COLLECTION | MongoDB collection for Gunicorn logs | gunicorn_logs |
| AUDIT_LOGS_ASYNC_LOGGING | Enable asynchronous logging with Celery | False |
| AUDIT_CELERY_QUEUE | Celery queue name for audit logging tasks | audit_logs |
| AUDIT_LOGGER_MAX_BODY_LENGTH | Maximum length for request/response bodies | 8192 |
| AUDIT_LOGS_SAVE_FULL_BODY | Save complete request/response bodies without truncation | False |
| AUDIT_LOGGER_ERROR_EMAIL_SENDER | Email sender for error notifications | alerts@yourdomain.com |
| AUDIT_LOGGER_ERROR_EMAIL_RECIPIENTS | Email recipients for error notifications | admin@yourdomain.com |
| AUDIT_LOGGER_RAISE_EXCEPTIONS | Raise exceptions instead of logging them | False |

## Body Size Configuration

By default, Django Audit Logger truncates request and response bodies to 8192 bytes to prevent excessive database usage. You can customize this behavior in two ways:

1. **Adjust the maximum body length**:
   ```python
   # In your Django settings
   AUDIT_LOGGER_MAX_BODY_LENGTH = 16384  # 16KB
   ```

2. **Save complete bodies without truncation**:
   ```python
   # In your Django settings
   AUDIT_LOGS_SAVE_FULL_BODY = True
   ```

When `AUDIT_LOGS_SAVE_FULL_BODY` is enabled, the entire request and response bodies will be saved regardless of size. This is particularly useful when:

- You need complete audit trails for compliance purposes
- You're debugging complex API interactions
- You're using MongoDB as your storage backend, which handles large documents efficiently

**Note**: Enabling this option may significantly increase storage requirements, especially for high-traffic applications with large payloads.
