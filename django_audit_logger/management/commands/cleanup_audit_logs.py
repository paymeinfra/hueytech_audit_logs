"""
Management command to clean up old audit logs.
"""
import logging
from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from ...models import RequestLog

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean up old audit logs based on retention period'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=None,
            help='Number of days to keep logs (default: from settings or 90 days)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform a dry run without deleting any data'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Batch size for deletion (default: 1000)'
        )

    def handle(self, *args, **options):
        # Get retention period from options, settings, or default
        days = options['days']
        if days is None:
            audit_logger_settings = getattr(settings, 'AUDIT_LOGGER', {})
            days = audit_logger_settings.get('RETENTION_DAYS', 90)
        
        if days <= 0:
            raise CommandError('Retention period must be a positive number of days')
        
        # Calculate cutoff date
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Get batch size
        batch_size = options['batch_size']
        
        # Get total count for logs to be deleted
        total_count = RequestLog.objects.filter(timestamp__lt=cutoff_date).count()
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would delete {total_count} logs older than {cutoff_date.isoformat()}'
                )
            )
            return
        
        if total_count == 0:
            self.stdout.write(
                self.style.SUCCESS(f'No logs found older than {cutoff_date.isoformat()}')
            )
            return
        
        self.stdout.write(
            self.style.WARNING(
                f'Deleting {total_count} logs older than {cutoff_date.isoformat()}'
            )
        )
        
        # Delete in batches to avoid memory issues
        deleted_count = 0
        while True:
            with transaction.atomic():
                # Get IDs for the batch
                ids = list(
                    RequestLog.objects.filter(timestamp__lt=cutoff_date)
                    .values_list('id', flat=True)[:batch_size]
                )
                
                if not ids:
                    break
                
                # Delete the batch
                deleted_batch = RequestLog.objects.filter(id__in=ids).delete()[0]
                deleted_count += deleted_batch
                
                self.stdout.write(
                    f'Deleted batch of {deleted_batch} logs ({deleted_count}/{total_count})'
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully deleted {deleted_count} logs')
        )
