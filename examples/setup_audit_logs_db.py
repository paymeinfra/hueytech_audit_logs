#!/usr/bin/env python
"""
Script to set up the audit logs database and run migrations.
This script should be run after installing the Django Audit Logger package.
"""
import os
import sys
import argparse
import subprocess
import logging
from pathlib import Path
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('audit_logs_setup')

# Load environment variables from .env file
load_dotenv()


def check_postgres_installed():
    """Check if PostgreSQL is installed."""
    try:
        result = subprocess.run(['which', 'psql'], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("PostgreSQL is not installed or not in PATH. Please install PostgreSQL.")
            return False
        return True
    except Exception as e:
        logger.error(f"Error checking PostgreSQL installation: {e}")
        return False


def create_database(db_name, db_user, db_password, db_host, db_port):
    """Create the audit logs database if it doesn't exist."""
    logger.info(f"Checking if database '{db_name}' exists...")
    
    # Check if database exists
    check_cmd = [
        'psql',
        '-h', db_host,
        '-p', db_port,
        '-U', db_user,
        '-c', f"SELECT 1 FROM pg_database WHERE datname = '{db_name}';"
    ]
    
    # Set PGPASSWORD environment variable for the subprocess
    env = os.environ.copy()
    env['PGPASSWORD'] = db_password
    
    try:
        result = subprocess.run(check_cmd, capture_output=True, text=True, env=env)
        if ' 1 ' in result.stdout:
            logger.info(f"Database '{db_name}' already exists.")
            return True
        
        # Create database
        logger.info(f"Creating database '{db_name}'...")
        create_cmd = [
            'psql',
            '-h', db_host,
            '-p', db_port,
            '-U', db_user,
            '-c', f"CREATE DATABASE {db_name};"
        ]
        
        result = subprocess.run(create_cmd, capture_output=True, text=True, env=env)
        if result.returncode == 0:
            logger.info(f"Database '{db_name}' created successfully.")
            return True
        else:
            logger.error(f"Failed to create database: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error creating database: {e}")
        return False


def run_migrations(project_path, db_name):
    """Run migrations for the audit logs database."""
    logger.info("Running migrations for the audit logs database...")
    
    try:
        # Change to the project directory
        os.chdir(project_path)
        
        # Run migrations
        cmd = [
            'python', 'manage.py', 'migrate', 'django_audit_logger', '--database=audit_logs'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("Migrations completed successfully.")
            return True
        else:
            logger.error(f"Failed to run migrations: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        return False


def update_settings(project_path):
    """Check if the project settings include the database router."""
    settings_path = None
    
    # Try to find the settings file
    for root, dirs, files in os.walk(project_path):
        for file in files:
            if file == 'settings.py':
                settings_path = os.path.join(root, file)
                break
        if settings_path:
            break
    
    if not settings_path:
        logger.error("Could not find settings.py in the project directory.")
        return False
    
    # Check if the database router is already configured
    with open(settings_path, 'r') as f:
        settings_content = f.read()
    
    if 'django_audit_logger.routers.AuditLogRouter' in settings_content:
        logger.info("Database router is already configured in settings.")
        return True
    
    # Check if DATABASES and DATABASE_ROUTERS are defined
    if 'DATABASES' not in settings_content:
        logger.error("DATABASES setting not found in settings.py.")
        return False
    
    # Provide instructions for manual configuration
    logger.info("\nPlease add the following to your settings.py file:")
    logger.info("\n# Add audit_logs database configuration")
    logger.info("DATABASES['audit_logs'] = {")
    logger.info("    'ENGINE': 'django.db.backends.postgresql',")
    logger.info("    'NAME': os.environ.get('AUDIT_LOGS_DB_NAME', 'audit_logs_db'),")
    logger.info("    'USER': os.environ.get('AUDIT_LOGS_DB_USER', 'postgres'),")
    logger.info("    'PASSWORD': os.environ.get('AUDIT_LOGS_DB_PASSWORD', ''),")
    logger.info("    'HOST': os.environ.get('AUDIT_LOGS_DB_HOST', 'localhost'),")
    logger.info("    'PORT': os.environ.get('AUDIT_LOGS_DB_PORT', '5432'),")
    logger.info("}")
    logger.info("\n# Configure the database router")
    logger.info("DATABASE_ROUTERS = ['django_audit_logger.routers.AuditLogRouter']")
    
    return True


def main():
    """Main function to set up the audit logs database."""
    parser = argparse.ArgumentParser(description='Set up the audit logs database for Django Audit Logger.')
    parser.add_argument('--project-path', type=str, help='Path to the Django project')
    parser.add_argument('--db-name', type=str, help='Audit logs database name')
    parser.add_argument('--db-user', type=str, help='Database user')
    parser.add_argument('--db-password', type=str, help='Database password')
    parser.add_argument('--db-host', type=str, default='localhost', help='Database host')
    parser.add_argument('--db-port', type=str, default='5432', help='Database port')
    
    args = parser.parse_args()
    
    # Get values from arguments or environment variables
    project_path = args.project_path or os.getcwd()
    db_name = args.db_name or os.environ.get('AUDIT_LOGS_DB_NAME', 'audit_logs_db')
    db_user = args.db_user or os.environ.get('AUDIT_LOGS_DB_USER', 'postgres')
    db_password = args.db_password or os.environ.get('AUDIT_LOGS_DB_PASSWORD', '')
    db_host = args.db_host or os.environ.get('AUDIT_LOGS_DB_HOST', 'localhost')
    db_port = args.db_port or os.environ.get('AUDIT_LOGS_DB_PORT', '5432')
    
    logger.info("Setting up audit logs database...")
    logger.info(f"Project path: {project_path}")
    logger.info(f"Database: {db_name} on {db_host}:{db_port}")
    
    # Check if PostgreSQL is installed
    if not check_postgres_installed():
        sys.exit(1)
    
    # Create the database
    if not create_database(db_name, db_user, db_password, db_host, db_port):
        sys.exit(1)
    
    # Update settings
    if not update_settings(project_path):
        sys.exit(1)
    
    # Run migrations
    if not run_migrations(project_path, db_name):
        sys.exit(1)
    
    logger.info("Audit logs database setup completed successfully!")


if __name__ == '__main__':
    main()
