"""
Example Django settings file showing how to configure Django Audit Logger.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'your-secret-key-here')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Add the Django Audit Logger app
    'django_audit_logger',
    
    # Your apps
    'your_app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # Add the Django Audit Logger middleware
    'django_audit_logger.middleware.RequestLogMiddleware',
]

ROOT_URLCONF = 'your_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'your_project.wsgi.application'

# Database configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'your_main_db'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    },
    # Separate database for audit logs
    'audit_logs': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('AUDIT_LOGS_DB_NAME', 'audit_logs_db'),
        'USER': os.environ.get('AUDIT_LOGS_DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('AUDIT_LOGS_DB_PASSWORD', ''),
        'HOST': os.environ.get('AUDIT_LOGS_DB_HOST', 'localhost'),
        'PORT': os.environ.get('AUDIT_LOGS_DB_PORT', '5432'),
    }
}

# Configure the database router
DATABASE_ROUTERS = ['django_audit_logger.routers.AuditLogRouter']

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django Audit Logger Settings
AUDIT_LOGGER_EXCLUDE_PATHS = [
    r'^/static/',
    r'^/media/',
    r'^/favicon\.ico$',
    r'^/admin/jsi18n/',
]

AUDIT_LOGGER_MAX_BODY_LENGTH = int(os.environ.get('AUDIT_LOGGER_MAX_BODY_LENGTH', '8192'))

# Email notification settings for Django Audit Logger
AUDIT_LOGGER_ERROR_EMAIL_SENDER = os.environ.get('AUDIT_LOGGER_ERROR_EMAIL_SENDER')
AUDIT_LOGGER_ERROR_EMAIL_RECIPIENTS = os.environ.get('AUDIT_LOGGER_ERROR_EMAIL_RECIPIENTS')
AUDIT_LOGGER_RAISE_EXCEPTIONS = os.environ.get('AUDIT_LOGGER_RAISE_EXCEPTIONS', 'False').lower() == 'true'

# AWS Settings for SES
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_SES_REGION_NAME = os.environ.get('AWS_SES_REGION_NAME', 'us-east-1')

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(os.environ.get('GUNICORN_LOG_DIR', '/var/log/django'), 'django.log'),
            'maxBytes': int(os.environ.get('GUNICORN_LOG_MAX_BYTES', '10485760')),  # 10MB
            'backupCount': int(os.environ.get('GUNICORN_LOG_BACKUP_COUNT', '10')),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': True,
        },
        'django_audit_logger': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
