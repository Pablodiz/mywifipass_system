# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

"""
Signal handlers for token cleanup and security-related events.

SECURITY: These signals ensure that expired tokens are automatically
cleaned from the database when new tokens are created.
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from mywifipass.api.auth_model import LoginToken

logger = logging.getLogger(__name__)


@receiver(post_save, sender=LoginToken)
def cleanup_old_tokens_on_new_token(sender, instance, created, **kwargs):
    """
    Cleanup expired tokens when a new token is created.
    
    This provides opportunistic cleanup - whenever a user creates a new
    login token (e.g., scanning QR code again), we take the opportunity
    to clean up any stale tokens from previous attempts.
    
    Regular cleanup via management command is still recommended for
    production deployments.
    """
    if created:
        try:
            # Delete tokens that expired more than 1 hour ago
            # (keep some buffer to avoid aggressive cleanup)
            cutoff_time = timezone.now() - timezone.timedelta(hours=1)
            expired_count = LoginToken.objects.filter(
                expires_at__lt=cutoff_time
            ).delete()[0]
            
            if expired_count > 0:
                logger.debug(f"Token cleanup: Removed {expired_count} old tokens")
        except Exception as e:
            logger.warning(f"Failed to cleanup old tokens: {str(e)}")
