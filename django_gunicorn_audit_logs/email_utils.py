"""
Email utilities for the Django Gunicorn Audit Logs package.
"""
import os
import logging
import traceback
from typing import Callable, Any, Optional, Dict

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    class ClientError(Exception):
        """Placeholder for boto3.ClientError when boto3 is not available."""
        pass

try:
    from django.conf import settings
    DJANGO_AVAILABLE = True
except ImportError:
    DJANGO_AVAILABLE = False

try:
    from dotenv import load_dotenv
    # Load environment variables from .env file
    load_dotenv()
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

logger = logging.getLogger(__name__)


def send_error_email(subject: str, error_message: str, traceback_info: Optional[str] = None) -> bool:
    """
    Send an error notification email using AWS SES.
    
    Args:
        subject (str): Email subject
        error_message (str): Error message
        traceback_info (str, optional): Traceback information
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    # Check if required dependencies are available
    if not BOTO3_AVAILABLE:
        logger.error("boto3 package is not installed. Cannot send error emails.")
        return False
    
    if not DJANGO_AVAILABLE and not DOTENV_AVAILABLE:
        logger.error("Neither Django nor python-dotenv is available for configuration.")
        return False
    
    # Get email configuration from settings or environment variables
    sender = None
    recipients_str = None
    
    if DJANGO_AVAILABLE:
        sender = getattr(settings, 'AUDIT_LOGS_ERROR_EMAIL_SENDER', None)
        recipients_str = getattr(settings, 'AUDIT_LOGS_ERROR_EMAIL_RECIPIENTS', None)
    
    # Fall back to environment variables if not found in settings
    if not sender:
        sender = os.environ.get('AUDIT_LOGS_ERROR_EMAIL_SENDER')
    
    if not recipients_str:
        recipients_str = os.environ.get('AUDIT_LOGS_ERROR_EMAIL_RECIPIENTS', '')
    
    # Check if email sending is enabled
    if not sender or not recipients_str:
        logger.warning("Error email notification is not configured. Set AUDIT_LOGS_ERROR_EMAIL_SENDER and AUDIT_LOGS_ERROR_EMAIL_RECIPIENTS.")
        return False
    
    # Convert recipients string to list
    recipients = [r.strip() for r in recipients_str.split(',') if r.strip()]
    
    # Prepare email content
    body_text = f"""
Error in Django Gunicorn Audit Logs:

{error_message}

"""
    
    if traceback_info:
        body_text += f"""
Traceback:
{traceback_info}
"""
    
    # Add environment information
    body_text += f"""
Environment: {os.environ.get('DJANGO_SETTINGS_MODULE', 'Unknown')}
Server: {os.environ.get('HOSTNAME', 'Unknown')}
"""
    
    # Get AWS region from settings or environment
    aws_region = None
    if DJANGO_AVAILABLE:
        aws_region = getattr(settings, 'AUDIT_LOGS_AWS_SES_REGION_NAME', None)
    
    if not aws_region:
        aws_region = os.environ.get('AUDIT_LOGS_AWS_SES_REGION_NAME', 'us-east-1')
    
    try:
        # Read AWS credentials from environment variables
        aws_access_key = os.environ.get('AUDIT_LOGS_AWS_ACCESS_KEY_ID')
        aws_secret_key = os.environ.get('AUDIT_LOGS_AWS_SECRET_ACCESS_KEY')
        
        # Check if credentials are available
        if not aws_access_key or not aws_secret_key:
            logger.error("AWS credentials not found in environment variables")
            return False
        
        ses_client = boto3.client(
            'ses',
            region_name=aws_region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
        
        # Prepare email
        email_message = {
            'Subject': {
                'Data': f"[Django Gunicorn Audit Logs Error] {subject}"
            },
            'Body': {
                'Text': {
                    'Data': body_text
                }
            }
        }
        
        # Send email
        response = ses_client.send_email(
            Source=sender,
            Destination={
                'ToAddresses': recipients
            },
            Message=email_message
        )
        
        logger.info("Error notification email sent. MessageId: %s", response.get('MessageId'))
        return True
        
    except ClientError as e:
        logger.error("Failed to send error notification email: %s", e)
        return False
    except (ValueError, TypeError, AttributeError, KeyError, ConnectionError) as e:
        logger.error("Error preparing email notification: %s", e)
        return False


def capture_exception_and_notify(func: Callable) -> Callable:
    """
    Decorator to capture exceptions and send email notifications.
    
    Args:
        func: The function to decorate
        
    Returns:
        The decorated function
    """
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except (ValueError, TypeError, AttributeError, KeyError, OSError, ConnectionError) as e:
            # Get traceback information
            tb = traceback.format_exc()
            
            # Log the error
            logger.error("Exception in %s: %s\n%s", func.__name__, str(e), tb)
            
            # Send email notification
            send_error_email(
                f"Exception in {func.__name__}",
                f"An exception occurred in {func.__name__}: {str(e)}",
                tb
            )
            
            # Re-raise the exception if configured to do so
            if os.environ.get('AUDIT_LOGS_RAISE_EXCEPTIONS', 'False').lower() == 'true':
                raise
            
    return wrapper
