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


def send_email_on_networks_changed(sender, instance, action, reverse, model, pk_set, **kwargs):
    """
    Send email to user when networks are assigned to them (post_add action).
    
    This signal is triggered after ManyToMany relationships are saved.
    We use this instead of the save() method because Django admin saves
    ManyToMany relationships AFTER the model's save() method completes.
    
    Args:
        sender: The ManyToMany through model
        instance: The WifiUser instance being modified
        action: The action performed ('post_add', 'post_remove', 'post_clear', etc)
        pk_set: The set of primary keys being changed
        **kwargs: Additional arguments
    """
    from mywifipass.models import WifiUser
    from mywifipass.utils import send_mail
    
    # Only process WifiUser model and only on post_add action (networks being added)
    if not isinstance(instance, WifiUser):
        return
    
    # Only send emails when networks are added ('post_add')
    if action != 'post_add':
        return
    
    try:
        # Check if user should receive emails
        if not instance.email_sent and instance.networks.exists():
            # Get networks that have auto-send enabled
            auto_send_networks = instance.networks.filter(send_emails_automatically=True)
            
            if auto_send_networks.exists():
                # Send email for each network with auto-send enabled
                for network in auto_send_networks:
                    send_mail(instance, update=False, network=network)
                
                # Mark email as sent
                instance.email_sent = True
                instance.email_sent_date = timezone.now()
                instance.save(update_fields=['email_sent', 'email_sent_date'], send_email=False)
                
                logger.info(f"Auto-sent email to user {instance.email} for {auto_send_networks.count()} network(s)")
    except Exception as e:
        logger.error(f"Error sending email to user {instance.email}: {str(e)}")


