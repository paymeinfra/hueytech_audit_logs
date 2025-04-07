"""
Views for testing the Django Audit Logger package.
"""
import json
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt


def test_view(request):
    """
    Simple test view that returns a plain text response.
    """
    return HttpResponse("Test view response", content_type="text/plain")


@csrf_exempt
def test_api_view(request):
    """
    Test API view that handles different HTTP methods and JSON data.
    """
    if request.method == 'GET':
        return JsonResponse({
            'message': 'This is a GET response',
            'query_params': dict(request.GET.items())
        })
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            data = {}
        
        return JsonResponse({
            'message': 'This is a POST response',
            'received_data': data
        })
    
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            data = {}
        
        return JsonResponse({
            'message': 'This is a PUT response',
            'received_data': data
        })
    
    elif request.method == 'DELETE':
        return JsonResponse({
            'message': 'This is a DELETE response'
        })
    
    return JsonResponse({
        'error': 'Unsupported method'
    }, status=405)


def test_error_view(request):
    """
    Test view that raises an exception to test error logging.
    """
    # Deliberately raise an exception
    raise ValueError("This is a test exception")
