"""
Tests for the Django Audit Logger utility functions.
"""
import json
from unittest.mock import Mock
from django.test import TestCase
from django_audit_logger.utils import get_client_ip, get_user_id, mask_sensitive_data, truncate_data


class TestUtils(TestCase):
    """
    Test cases for utility functions.
    """
    
    def test_get_client_ip(self):
        """
        Test the get_client_ip function with various scenarios.
        """
        # Test with X-Forwarded-For header
        request = Mock()
        request.META = {
            'HTTP_X_FORWARDED_FOR': '192.168.1.1, 10.0.0.1',
            'REMOTE_ADDR': '127.0.0.1'
        }
        self.assertEqual(get_client_ip(request), '192.168.1.1')
        
        # Test with only REMOTE_ADDR
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        self.assertEqual(get_client_ip(request), '127.0.0.1')
        
        # Test with empty META
        request.META = {}
        self.assertIsNone(get_client_ip(request))
    
    def test_get_user_id(self):
        """
        Test the get_user_id function with various scenarios.
        """
        # Test with authenticated user
        request = Mock()
        user = Mock()
        user.is_authenticated = True
        user.id = 123
        user.username = 'testuser'
        user.email = 'test@example.com'
        request.user = user
        
        self.assertEqual(get_user_id(request), '123')
        
        # Test with unauthenticated user
        user.is_authenticated = False
        self.assertIsNone(get_user_id(request))
        
        # Test with auth token
        request = Mock()
        auth = Mock()
        auth.get_user_id = lambda: '456'
        request.auth = auth
        self.assertEqual(get_user_id(request), '456')
        
        # Test with no user or auth
        request = Mock()
        self.assertIsNone(get_user_id(request))
    
    def test_mask_sensitive_data_dict(self):
        """
        Test masking sensitive data in dictionaries.
        """
        data = {
            'username': 'testuser',
            'password': 'secret123',
            'token': 'abc123xyz',
            'email': 'test@example.com'
        }
        
        sensitive_fields = ['password', 'token']
        masked = mask_sensitive_data(data, sensitive_fields)
        
        self.assertEqual(masked['username'], 'testuser')
        self.assertEqual(masked['password'], '********')
        self.assertEqual(masked['token'], '********')
        self.assertEqual(masked['email'], 'test@example.com')
    
    def test_mask_sensitive_data_json(self):
        """
        Test masking sensitive data in JSON strings.
        """
        data = json.dumps({
            'username': 'testuser',
            'password': 'secret123',
            'token': 'abc123xyz',
            'email': 'test@example.com'
        })
        
        sensitive_fields = ['password', 'token']
        masked = mask_sensitive_data(data, sensitive_fields)
        
        # Parse the masked JSON back to a dict
        masked_dict = json.loads(masked)
        
        self.assertEqual(masked_dict['username'], 'testuser')
        self.assertEqual(masked_dict['password'], '********')
        self.assertEqual(masked_dict['token'], '********')
        self.assertEqual(masked_dict['email'], 'test@example.com')
    
    def test_mask_sensitive_data_form(self):
        """
        Test masking sensitive data in form-encoded strings.
        """
        data = 'username=testuser&password=secret123&token=abc123xyz&email=test@example.com'
        
        sensitive_fields = ['password', 'token']
        masked = mask_sensitive_data(data, sensitive_fields)
        
        self.assertIn('username=testuser', masked)
        self.assertIn('password=********', masked)
        self.assertIn('token=********', masked)
        self.assertIn('email=test@example.com', masked)
    
    def test_truncate_data(self):
        """
        Test the truncate_data function.
        """
        # Test with data shorter than max length
        data = 'Short data'
        self.assertEqual(truncate_data(data, 20), 'Short data')
        
        # Test with data longer than max length
        data = 'This is a very long string that should be truncated'
        truncated = truncate_data(data, 20)
        self.assertEqual(truncated, 'This is a very long ... [truncated]')
        self.assertTrue(len(truncated) > 20)  # Account for the suffix
        
        # Test with None
        self.assertIsNone(truncate_data(None, 20))
        
        # Test with non-string
        data = 123
        self.assertEqual(truncate_data(data, 20), 123)
