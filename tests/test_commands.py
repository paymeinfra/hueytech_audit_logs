"""
Tests for the Django Audit Logger management commands.
"""
from datetime import timedelta
from io import StringIO
from django.test import TestCase
from django.core.management import call_command
from django.utils import timezone
from django_audit_logger.models import RequestLog


class TestCleanupCommand(TestCase):
    """
    Test cases for the cleanup_audit_logs management command.
    """
    
    def setUp(self):
        """
        Set up test data with logs of different ages.
        """
        # Create logs with different timestamps
        now = timezone.now()
        
        # Current logs (should be kept)
        for i in range(5):
            RequestLog.objects.create(
                timestamp=now - timedelta(days=i),
                method='GET',
                path=f'/test/{i}/',
                status_code=200
            )
        
        # Old logs (should be deleted)
        for i in range(5):
            RequestLog.objects.create(
                timestamp=now - timedelta(days=100 + i),
                method='GET',
                path=f'/old/{i}/',
                status_code=200
            )
    
    def test_cleanup_command(self):
        """
        Test that the cleanup command deletes old logs.
        """
        # Verify initial count
        self.assertEqual(RequestLog.objects.count(), 10)
        
        # Run the command with 30 days retention
        out = StringIO()
        call_command('cleanup_audit_logs', days=30, stdout=out)
        
        # Verify that old logs were deleted
        self.assertEqual(RequestLog.objects.count(), 5)
        
        # All remaining logs should be newer than 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        self.assertEqual(
            RequestLog.objects.filter(timestamp__lt=thirty_days_ago).count(),
            0
        )
    
    def test_dry_run(self):
        """
        Test that the dry run option doesn't delete any logs.
        """
        # Verify initial count
        self.assertEqual(RequestLog.objects.count(), 10)
        
        # Run the command with dry run
        out = StringIO()
        call_command('cleanup_audit_logs', days=30, dry_run=True, stdout=out)
        
        # Verify that no logs were deleted
        self.assertEqual(RequestLog.objects.count(), 10)
    
    def test_batch_size(self):
        """
        Test that the batch size option works correctly.
        """
        # Create many more logs
        now = timezone.now()
        for i in range(20):
            RequestLog.objects.create(
                timestamp=now - timedelta(days=100 + i),
                method='GET',
                path=f'/batch/{i}/',
                status_code=200
            )
        
        # Verify initial count
        self.assertEqual(RequestLog.objects.count(), 30)
        
        # Run the command with batch size of 5
        out = StringIO()
        call_command('cleanup_audit_logs', days=30, batch_size=5, stdout=out)
        
        # Verify that old logs were deleted
        self.assertEqual(RequestLog.objects.count(), 5)
        
        # All remaining logs should be newer than 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        self.assertEqual(
            RequestLog.objects.filter(timestamp__lt=thirty_days_ago).count(),
            0
        )
