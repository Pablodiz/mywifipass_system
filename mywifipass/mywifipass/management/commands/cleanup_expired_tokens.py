# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from mywifipass.api.auth_model import LoginToken

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Management command to clean up expired login tokens from the database.
    
    SECURITY: This command removes stale authentication tokens that could be 
    exploited if leaked. Should be run periodically (e.g., via cron, hourly).
    
    Usage:
        python manage.py cleanup_expired_tokens
    
    Or add to crontab:
        0 * * * * cd /path/to/app && python manage.py cleanup_expired_tokens
    
    """
    
    help = 'Clean up expired login tokens from the database'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
    
    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        # Find all expired tokens
        expired_tokens = LoginToken.objects.filter(
            expires_at__lt=timezone.now()
        )
        
        count = expired_tokens.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('✓ No expired tokens found.')
            )
            logger.info("cleanup_expired_tokens: No expired tokens to clean up")
            return
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Would delete {count} expired tokens')
            )
            logger.info(f"cleanup_expired_tokens (dry-run): {count} tokens would be deleted")
            return
        
        # Delete expired tokens
        deleted_count, _ = expired_tokens.delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'✓ Deleted {deleted_count} expired login token(s)')
        )
        logger.info(f"cleanup_expired_tokens: Successfully deleted {deleted_count} tokens")
