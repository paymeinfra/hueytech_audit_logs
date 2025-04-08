<div align="center">
  <h1>🔍 Django Gunicorn Audit Logs</h1>
  <p>Production-grade Django package for comprehensive request/response logging with PostgreSQL and MongoDB support</p>
</div>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python" alt="Python Version">
  <img src="https://img.shields.io/badge/Django-3.2%2B-green?style=for-the-badge&logo=django" alt="Django Version">
  <img src="https://img.shields.io/badge/Gunicorn-20.1%2B-red?style=for-the-badge&logo=gunicorn" alt="Gunicorn Version">
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License">
  <br>
  <img src="https://img.shields.io/badge/CI-passing-brightgreen?style=flat-square" alt="CI Status">
  <img src="https://codecov.io/gh/paymeinfra/hueytech_audit_logs/branch/main/graph/badge.svg" alt="Code Coverage">
</p>

<p align="center">
  <a href="#-key-features">Features</a> •
  <a href="#-installation">Installation</a> •
  <a href="#-configuration">Configuration</a> •
  <a href="#-production-deployment">Deployment</a> •
  <a href="#-usage-examples">Examples</a> •
  <a href="#-mongodb-support">MongoDB</a> •
  <a href="#-performance">Performance</a>
</p>

---

## 🌟 Key Features

<div align="center">
  <table>
    <tr>
      <td align="center">📝 Comprehensive Logging</td>
      <td align="center">🔒 Security Features</td>
      <td align="center">⚡ Performance Optimized</td>
      <td align="center">🔄 Dual Storage</td>
    </tr>
    <tr>
      <td align="center">📊 Admin Interface</td>
      <td align="center">🔧 Configurable Options</td>
      <td align="center">🚀 Async Processing</td>
      <td align="center">🧹 Auto Maintenance</td>
    </tr>
  </table>
</div>

### 📝 Comprehensive Logging
- ✨ Detailed HTTP request and response logging
- 🔍 Full request/response body capture
- 📄 Headers and metadata recording
- 🕒 Performance timing metrics
- 📂 Dual logging system (database + file-based)
- 🔄 120-day retention policy for database logs

### 🔒 Security Features
- 🔐 Sensitive data masking (passwords, tokens, etc.)
- 🛡️ Configurable field exclusions
- 🔑 User identification and tracking
- 🚫 Path and extension filtering
- 🔍 Proper error handling to prevent information leakage

### 🔄 Dual Storage Support
- 💾 PostgreSQL primary storage
- 🍃 MongoDB optional storage
- ☁️ Write to both databases simultaneously
- 🔄 Automatic fallback mechanisms
- 📊 Optimized indexes for query performance

### 🚀 Performance Features
- ⚡ Asynchronous logging with Celery
- 📦 Batched database operations
- 🧠 Memory-efficient processing
- ⏱️ Minimal request cycle impact
- 🔍 Exclusion of static files and non-essential paths
- 📏 Body length limitations
- 🔄 Database maintenance and optimization
- 📋 Dedicated Celery queue for audit logging tasks

## 🛠️ Technical Stack

<div align="center">
  <table>
    <tr>
      <td align="center">
        <img src="https://img.shields.io/badge/Framework-Django-green?style=flat-square&logo=django" alt="Django">
      </td>
      <td align="center">
        <img src="https://img.shields.io/badge/Server-Gunicorn-red?style=flat-square&logo=gunicorn" alt="Gunicorn">
      </td>
    </tr>
    <tr>
      <td align="center">
        <img src="https://img.shields.io/badge/Database-PostgreSQL-blue?style=flat-square&logo=postgresql" alt="PostgreSQL">
      </td>
      <td align="center">
        <img src="https://img.shields.io/badge/Database-MongoDB-green?style=flat-square&logo=mongodb" alt="MongoDB">
      </td>
    </tr>
    <tr>
      <td align="center">
        <img src="https://img.shields.io/badge/Task%20Queue-Celery-brightgreen?style=flat-square&logo=celery" alt="Celery">
      </td>
      <td align="center">
        <img src="https://img.shields.io/badge/Logging-Rotating%20Files-orange?style=flat-square&logo=text-file" alt="Rotating Files">
      </td>
    </tr>
  </table>
</div>

## 🚀 Installation

<details>
<summary>From your organization's repository</summary>

```bash
pip install django-gunicorn-audit-logs --extra-index-url=https://your-org-repo-url/simple/
```
</details>

<details>
<summary>Development installation</summary>

```bash
git clone https://github.com/paymeinfra/hueytech_audit_logs.git
cd hueytech_audit_logs
pip install -e .
```
</details>

## ⚙️ Configuration

### Django Settings

Add the following to your Django settings:

```python
INSTALLED_APPS = [
    # ... other apps
    'django_gunicorn_audit_logs',
]

MIDDLEWARE = [
    # ... other middleware
    'django_gunicorn_audit_logs.middleware.RequestLogMiddleware',
]

# Audit Logger Settings
AUDIT_LOGS = {
    'ENABLED': True,
    'SENSITIVE_FIELDS': ['password', 'token', 'access_key', 'secret'],
    'USER_ID_CALLABLE': 'django_gunicorn_audit_logs.utils.get_user_id',
    'EXTRA_DATA_CALLABLE': None,  # Optional function to add custom data
}

# Enable asynchronous logging with Celery (optional)
AUDIT_LOGS_ASYNC_LOGGING = True
AUDIT_CELERY_QUEUE = "audit_logs"  # Dedicated Celery queue
```

### MongoDB Configuration (Optional)

```python
# MongoDB Settings
AUDIT_LOGS_USE_MONGO = True
AUDIT_LOGS_WRITE_TO_BOTH = True  # Write to both PostgreSQL and MongoDB
AUDIT_LOGS_MONGO_URI = "mongodb://username:password@host:port/database"
AUDIT_LOGS_MONGO_DB_NAME = "audit_logs"
AUDIT_LOGS_MONGO_REQUEST_LOGS_COLLECTION = "request_logs"
AUDIT_LOGS_MONGO_GUNICORN_LOGS_COLLECTION = "gunicorn_logs"
```

### Database Router Configuration

```python
# PostgreSQL Database Configuration
DATABASES = {
    'default': {
        # Your default database configuration
    },
    'audit_logs': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'audit_logs',
        'USER': 'audit_user',
        'PASSWORD': 'secure_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Optional: Configure Django to use a separate database for audit logs
DATABASE_ROUTERS = ['django_gunicorn_audit_logs.routers.AuditLogRouter']
```

## 🚀 Production Deployment

### Gunicorn Configuration

The package provides a custom Gunicorn logger that logs requests to both a rotating file and the database. During installation, the `gunicorn_config.py` file is automatically copied to your project directory.

```bash
# Basic Gunicorn configuration
gunicorn myproject.wsgi:application --config=gunicorn_config.py
```

### Environment Variables

```bash
# Basic Configuration
export AUDIT_LOGS_ENABLED=True
export AUDIT_LOGS_SAVE_FULL_BODY=False
export AUDIT_LOGGER_MAX_BODY_LENGTH=10000

# MongoDB Configuration
export AUDIT_LOGS_USE_MONGO=True
export AUDIT_LOGS_WRITE_TO_BOTH=True
export AUDIT_LOGS_MONGO_URI="mongodb://username:password@host:port/database"
export AUDIT_LOGS_MONGO_DB_NAME="audit_logs"
export AUDIT_LOGS_MONGO_REQUEST_LOGS_COLLECTION="request_logs"
export AUDIT_LOGS_MONGO_GUNICORN_LOGS_COLLECTION="gunicorn_logs"

# PostgreSQL Configuration
export AUDIT_LOGS_DB_NAME="audit_logs"
export AUDIT_LOGS_DB_USER="audit_user"
export AUDIT_LOGS_DB_PASSWORD="secure_password"
export AUDIT_LOGS_DB_HOST="localhost"
export AUDIT_LOGS_DB_PORT="5432"

# Gunicorn Configuration
export GUNICORN_BIND="0.0.0.0:8000"
export GUNICORN_WORKERS="4"
export GUNICORN_WORKER_CLASS="sync"
export GUNICORN_TIMEOUT="30"
export GUNICORN_LOG_LEVEL="info"
export GUNICORN_LOG_DIR="/var/log/gunicorn"
export GUNICORN_LOG_MAX_BYTES=10485760
export GUNICORN_LOG_BACKUP_COUNT=10

# AWS Credentials (required for SES email notifications)
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_SES_REGION_NAME="us-east-1"  # AWS region for SES

# Email Configuration
export AUDIT_LOGGER_ERROR_EMAIL_SENDER="alerts@yourdomain.com"
export AUDIT_LOGGER_ERROR_EMAIL_RECIPIENTS="admin@yourdomain.com,devops@yourdomain.com"
export AUDIT_LOGGER_RAISE_EXCEPTIONS="False"  # Set to 'True' to re-raise exceptions after logging
```

## 📊 MongoDB Support

### Installation

To use MongoDB as a storage backend, install the required dependencies:

```bash
pip install pymongo dnspython
```

### Configuration

1. Enable MongoDB storage:
```python
AUDIT_LOGS_USE_MONGO = True
```

2. Configure MongoDB connection:
```python
AUDIT_LOGS_MONGO_URI = "mongodb://username:password@host:port/database"
AUDIT_LOGS_MONGO_DB_NAME = "audit_logs"
```

3. Optional: Enable dual-write mode:
```python
AUDIT_LOGS_WRITE_TO_BOTH = True  # Write to both PostgreSQL and MongoDB
```

### Usage with MongoDB

```python
from django_gunicorn_audit_logs.mongo_storage import mongo_storage

# Query logs from MongoDB
logs = mongo_storage.find_request_logs(
    filter={"path": "/api/users/", "status_code": {"$gte": 400}},
    limit=100,
    sort=[("created_at", -1)]
)

# Count logs
count = mongo_storage.count_request_logs(
    filter={"user_id": "user-123"}
)

# Delete old logs
mongo_storage.delete_old_request_logs(
    days=90
)
```

### Connecting to Different MongoDB Deployments

The package supports various MongoDB deployment types:

1. **Self-Managed MongoDB Cluster**:
   ```
   AUDIT_LOGS_MONGO_URI=mongodb://username:password@10.0.0.1:27017,10.0.0.2:27017,10.0.0.3:27017/?replicaSet=rs0&authSource=admin
   ```

2. **MongoDB Atlas (Cloud)**:
   ```
   AUDIT_LOGS_MONGO_URI=mongodb+srv://username:password@cluster0.example.mongodb.net/?retryWrites=true&w=majority
   ```

3. **Single Node Development**:
   ```
   AUDIT_LOGS_MONGO_URI=mongodb://localhost:27017/
   ```

### Query Examples

```python
# Import the MongoDB storage backend
from django_gunicorn_audit_logs.mongo_storage import mongo_storage

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
mongo_storage.delete_old_logs(days=90)
```

### Dual Storage Benefits

When using both PostgreSQL and MongoDB storage:

- **Redundancy**: Critical logs are preserved in both systems
- **Query Flexibility**: Use SQL or MongoDB queries depending on your needs
- **Migration Path**: Gradually transition from PostgreSQL to MongoDB while maintaining data integrity
- **Performance Optimization**: Use PostgreSQL for transactional integrity and MongoDB for high-throughput logging

### Performance Considerations

When dual storage is enabled, the system attempts to write to MongoDB first. If the MongoDB write succeeds, it proceeds to write to PostgreSQL. This approach ensures that the faster MongoDB write doesn't have to wait for the PostgreSQL write to complete.

## 🚀 Asynchronous Logging with Celery

### Installation

```bash
pip install celery
```

### Configuration

```python
# In settings.py
AUDIT_LOGS_ASYNC_LOGGING = True
AUDIT_CELERY_QUEUE = "audit_logs"  # Dedicated queue for audit logs

# In your Celery configuration
CELERY_TASK_ROUTES = {
    'django_gunicorn_audit_logs.tasks.*': {'queue': 'audit_logs'},
}
```

### Benefits

- Reduced request processing time
- Improved application responsiveness
- Better handling of logging spikes during high traffic
- Fault tolerance with automatic retries for failed log entries

### Retry Mechanism

The asynchronous logging system includes a robust retry mechanism for handling failures:

- **Automatic Retries**: Failed logging tasks are automatically retried up to 3 times
- **Exponential Backoff**: Each retry attempt waits longer before trying again
- **Error Notifications**: Persistent failures trigger email notifications to administrators
- **Dead Letter Queue**: Tasks that fail repeatedly are moved to a dead letter queue for manual inspection

### Scaling for High-Volume Applications

For high-volume applications, consider these optimizations:

1. **Database Partitioning**:
   ```sql
   -- Create a partitioned table
   CREATE TABLE audit_logs_partitioned (
     id SERIAL,
     timestamp TIMESTAMP,
     -- other fields
     PRIMARY KEY (id, timestamp)
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

## 💡 Usage Examples

<details>
<summary>Basic Usage</summary>

The middleware automatically logs all requests and responses. No additional code is required for basic logging.

```python
# The middleware is already capturing requests and responses
# You can query the logs as needed:

from django_gunicorn_audit_logs.models import RequestLog, GunicornLogModel

# Get all Django request logs
logs = RequestLog.objects.all()

# Filter logs by path
api_logs = RequestLog.objects.filter(path__startswith='/api/')

# Filter logs by status code
error_logs = RequestLog.objects.filter(status_code__gte=400)

# Filter logs by user
user_logs = RequestLog.objects.filter(user_id='user123')

# Get slow requests
slow_requests = RequestLog.objects.filter(response_ms__gt=1000)
```
</details>

<details>
<summary>Custom User ID Extraction</summary>

```python
# In your utils.py
def get_custom_user_id(request):
    # Custom logic to extract user ID
    if hasattr(request, 'user') and request.user.is_authenticated:
        return f"user-{request.user.id}"
    elif 'X-API-Key' in request.headers:
        return f"api-{request.headers['X-API-Key'][:8]}"
    return 'anonymous'

# In your settings.py
AUDIT_LOGS = {
    # ... other settings
    'USER_ID_CALLABLE': 'path.to.your.utils.get_custom_user_id',
}
```
</details>

<details>
<summary>Adding Custom Data to Logs</summary>

```python
def add_custom_data(request, response):
    data = {}
    
    # Add request-specific data
    if hasattr(request, 'tenant'):
        data['tenant_id'] = request.tenant.id
        
    # Add business context
    if hasattr(request, 'transaction_id'):
        data['transaction_id'] = request.transaction_id
        
    # Add performance metrics
    if hasattr(request, '_start_time'):
        data['db_query_count'] = len(connection.queries)
        
    return data

# In your settings.py
AUDIT_LOGS = {
    # ... other settings
    'EXTRA_DATA_CALLABLE': 'path.to.your.module.add_custom_data',
}
```
</details>

<details>
<summary>Log Maintenance</summary>

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

# Clean up only gunicorn logs
python manage.py cleanup_audit_logs --log-type=gunicorn
```
</details>

<details>
<summary>Custom Middleware Configuration</summary>

```python
# In your custom middleware.py
from django_gunicorn_audit_logs.middleware import RequestLogMiddleware

class CustomAuditMiddleware(RequestLogMiddleware):
    def _should_log_request(self, request):
        # Custom logic to determine if request should be logged
        if request.path.startswith('/health/'):
            return False
        return super()._should_log_request(request)
        
    def _capture_request_data(self, request):
        # Add custom data capture
        data = super()._capture_request_data(request)
        data['custom_field'] = 'custom_value'
        return data

# In your settings.py
MIDDLEWARE = [
    # ... other middleware
    'path.to.your.middleware.CustomAuditMiddleware',
]
```
</details>

<details>
<summary>Recommended Production Settings</summary>

```python
# Recommended production settings
AUDIT_LOGS = {
    'ENABLED': True,
    'SENSITIVE_FIELDS': ['password', 'token', 'api_key', 'secret', 'credit_card'],
    'EXCLUDE_PATHS': ['/health/', '/metrics/', '/static/', '/media/'],
    'EXCLUDE_EXTENSIONS': ['.jpg', '.png', '.gif', '.css', '.js', '.svg', '.woff', '.ttf'],
    'MAX_BODY_LENGTH': 5000,  # Limit body size for PostgreSQL storage
    'SAVE_FULL_BODY': False,  # Enable only if needed
}

# Use MongoDB for high-volume storage
AUDIT_LOGS_USE_MONGO = True
AUDIT_LOGS_MONGO_URI = "mongodb://username:password@host:port/database"

# Enable async logging with dedicated queue
AUDIT_LOGS_ASYNC_LOGGING = True
AUDIT_CELERY_QUEUE = "audit_logs"
```
</details>

## 🛠️ Advanced Configuration

<details>
<summary>Custom Masking for Sensitive Data</summary>

```python
def custom_mask_sensitive_data(data, sensitive_fields):
    """Custom function to mask sensitive data"""
    if not data or not isinstance(data, dict):
        return data
        
    result = data.copy()
    for key, value in data.items():
        if key in sensitive_fields:
            result[key] = '******'
        elif isinstance(value, dict):
            result[key] = custom_mask_sensitive_data(value, sensitive_fields)
        elif isinstance(value, list):
            result[key] = [
                custom_mask_sensitive_data(item, sensitive_fields) 
                if isinstance(item, dict) else item 
                for item in value
            ]
    return result

# In your settings.py
AUDIT_LOGS = {
    # ... other settings
    'MASK_FUNCTION': 'path.to.your.module.custom_mask_sensitive_data',
}
```
</details>

<details>
<summary>Custom Exception Handling</summary>

```python
def custom_exception_handler(exc, request=None, extra_data=None):
    """Custom exception handler for audit logging errors"""
    # Log to your monitoring system
    logger.error(f"Audit log error: {exc}", exc_info=True, extra={
        'request': request,
        'extra_data': extra_data
    })
    
    # Send notification
    send_alert_to_slack(f"Audit logging error: {exc}")
    
    # Don't raise the exception, just log it
    return False

# In your settings.py
AUDIT_LOGS = {
    # ... other settings
    'EXCEPTION_HANDLER': 'path.to.your.module.custom_exception_handler',
}
```
</details>

<details>
<summary>Custom Database Router</summary>

```python
# In your routers.py
class CustomAuditLogRouter:
    """Custom database router for audit logs"""
    
    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'django_gunicorn_audit_logs':
            # Use a read replica for queries
            return 'audit_logs_replica'
        return None
        
    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'django_gunicorn_audit_logs':
            return 'audit_logs'
        return None
        
    def allow_relation(self, obj1, obj2, **hints):
        return None
        
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'django_gunicorn_audit_logs':
            return db == 'audit_logs'
        return None

# In your settings.py
DATABASE_ROUTERS = ['path.to.your.routers.CustomAuditLogRouter']
```
</details>

<details>
<summary>Custom Implementations</summary>

- Implement custom storage backends
- Implement custom masking for sensitive data
- Add custom error handling and notifications

### Database Setup Script

The `examples/setup_audit_logs_db.py` script helps you set up a separate database for audit logs:

```bash
# Run the setup script
python examples/setup_audit_logs_db.py --project-path /path/to/your/project --db-name audit_logs_db
```
</details>

## Troubleshooting

### Common Issues

1. **Missing Dependencies**
   - Ensure boto3 is installed for email notifications: `pip install boto3`
   - Ensure python-dotenv is installed for environment variables: `pip install python-dotenv`

2. **Database Connection Issues**
   - Check database credentials in your .env file
   - Ensure the audit_logs database exists
   - Run migrations with: `python manage.py migrate django_gunicorn_audit_logs --database=audit_logs`

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

---

<div align="center">
  Made with 🖤 by The Alok
</div>
