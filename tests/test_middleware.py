"""
Tests for the Django Audit Logger middleware.
"""
import json
import pytest
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django_audit_logger.models import RequestLog


class TestAuditLogMiddleware(TestCase):
    """
    Test cases for the AuditLogMiddleware.
    """
    def setUp(self):
        self.client = Client()
    
    def test_get_request_logging(self):
        """
        Test that GET requests are properly logged.
        """
        # Make a GET request
        response = self.client.get(reverse('test_view'))
        self.assertEqual(response.status_code, 200)
        
        # Check that the request was logged
        logs = RequestLog.objects.all()
        self.assertEqual(logs.count(), 1)
        
        log = logs.first()
        self.assertEqual(log.method, 'GET')
        self.assertEqual(log.path, '/test/')
        self.assertEqual(log.status_code, 200)
        self.assertIsNotNone(log.timestamp)
        self.assertIsNotNone(log.response_time_ms)
    
    def test_post_request_logging(self):
        """
        Test that POST requests with JSON data are properly logged.
        """
        # Test data
        data = {
            'name': 'Test User',
            'email': 'test@example.com',
            'password': 'secret123'  # This should be masked
        }
        
        # Make a POST request
        response = self.client.post(
            reverse('test_api_view'),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        # Check that the request was logged
        logs = RequestLog.objects.all()
        self.assertEqual(logs.count(), 1)
        
        log = logs.first()
        self.assertEqual(log.method, 'POST')
        self.assertEqual(log.path, '/api/test/')
        self.assertEqual(log.status_code, 200)
        
        # Check that sensitive data was masked
        self.assertIn('password', log.body)
        self.assertNotIn('secret123', log.body)
        self.assertIn('********', log.body)
    
    def test_error_logging(self):
        """
        Test that errors are properly logged.
        """
        # Make a request that will cause an error
        with self.assertRaises(ValueError):
            self.client.get(reverse('test_error_view'))
        
        # Check that the request was logged despite the error
        logs = RequestLog.objects.all()
        self.assertEqual(logs.count(), 1)
        
        log = logs.first()
        self.assertEqual(log.method, 'GET')
        self.assertEqual(log.path, '/error/')
        self.assertEqual(log.status_code, 500)
    
    @override_settings(AUDIT_LOGGER={'ENABLED': False})
    def test_disabled_middleware(self):
        """
        Test that no logs are created when the middleware is disabled.
        """
        # Make a request
        response = self.client.get(reverse('test_view'))
        self.assertEqual(response.status_code, 200)
        
        # Check that no logs were created
        logs = RequestLog.objects.all()
        self.assertEqual(logs.count(), 0)
    
    @override_settings(AUDIT_LOGGER={'EXCLUDE_PATHS': ['/test/']})
    def test_excluded_path(self):
        """
        Test that excluded paths are not logged.
        """
        # Make a request to an excluded path
        response = self.client.get(reverse('test_view'))
        self.assertEqual(response.status_code, 200)
        
        # Check that no logs were created
        logs = RequestLog.objects.all()
        self.assertEqual(logs.count(), 0)
        
        # Make a request to a non-excluded path
        response = self.client.get(reverse('test_api_view'))
        self.assertEqual(response.status_code, 200)
        
        # Check that this request was logged
        logs = RequestLog.objects.all()
        self.assertEqual(logs.count(), 1)
    
    @override_settings(AUDIT_LOGGER={'LOG_REQUEST_BODY': False, 'LOG_RESPONSE_BODY': False})
    def test_body_logging_disabled(self):
        """
        Test that request and response bodies are not logged when disabled.
        """
        # Test data
        data = {'name': 'Test User', 'email': 'test@example.com'}
        
        # Make a POST request
        response = self.client.post(
            reverse('test_api_view'),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        # Check that the request was logged but without bodies
        logs = RequestLog.objects.all()
        self.assertEqual(logs.count(), 1)
        
        log = logs.first()
        self.assertIsNone(log.body)
        self.assertIsNone(log.response_body)
