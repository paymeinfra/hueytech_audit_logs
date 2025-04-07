"""
Example usage of Django Audit Logger with custom database router and error notifications.
"""
import os
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django_audit_logger.email_utils import capture_exception_and_notify

# Set up logging
logger = logging.getLogger('django_audit_logger')


@capture_exception_and_notify
def process_payment(payment_data):
    """
    Example function that processes a payment.
    This function is decorated with capture_exception_and_notify to catch exceptions
    and send error notifications via email.
    
    Args:
        payment_data (dict): Payment data
        
    Returns:
        dict: Result of payment processing
    """
    # Simulate payment processing
    logger.info("Processing payment for user %s", payment_data.get('user_id'))
    
    # Simulate a validation check that might fail
    if not payment_data.get('amount') or float(payment_data.get('amount', 0)) <= 0:
        raise ValueError("Invalid payment amount")
        
    # Process payment logic would go here
    
    return {
        'status': 'success',
        'transaction_id': 'txn_123456789',
        'amount': payment_data.get('amount'),
        'currency': payment_data.get('currency', 'USD'),
    }


@csrf_exempt
def payment_api_view(request):
    """
    Example API view that handles payment requests.
    The AuditLogMiddleware will automatically log this request and response.
    
    Args:
        request: Django request object
        
    Returns:
        JsonResponse: API response
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # Extract payment data from request
        payment_data = {
            'user_id': request.user.id if hasattr(request, 'user') and request.user.is_authenticated else None,
            'amount': request.POST.get('amount'),
            'currency': request.POST.get('currency', 'USD'),
            'card_token': request.POST.get('card_token'),
            'description': request.POST.get('description'),
        }
        
        # Process the payment (this function is decorated with capture_exception_and_notify)
        result = process_payment(payment_data)
        
        # Return success response
        return JsonResponse(result)
        
    except ValueError as e:
        # Handle validation errors
        logger.warning("Payment validation error: %s", str(e))
        return JsonResponse({'error': str(e)}, status=400)
        
    except Exception as e:
        # Handle unexpected errors
        logger.error("Payment processing error: %s", str(e))
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)


# Example of how to run migrations for the audit_logs database
def run_audit_log_migrations():
    """
    Example function showing how to run migrations for the audit_logs database.
    This should be run as a management command:
    
    python manage.py migrate django_audit_logger --database=audit_logs
    """
    from django.core.management import call_command
    
    # Run migrations for the audit_logs database
    call_command('migrate', 'django_audit_logger', database='audit_logs')
    
    logger.info("Audit log migrations completed successfully")


# Example of how to check audit log database connection
def check_audit_log_db_connection():
    """
    Example function to check if the audit_logs database connection is working.
    """
    from django.db import connections
    from django.db.utils import OperationalError
    
    try:
        # Attempt to connect to the audit_logs database
        connection = connections['audit_logs']
        connection.cursor()
        logger.info("Successfully connected to audit_logs database")
        return True
    except OperationalError:
        logger.error("Could not connect to audit_logs database")
        return False
