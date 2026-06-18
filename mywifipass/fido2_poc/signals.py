# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from mywifipass.models import WifiNetworkLocation
from .models import Fido2NetworkConfig

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Fido2NetworkConfig)
def activate_requires_validator_when_fido2_enabled(sender, instance, **kwargs):
    """
    Signal handler that automatically activates requires_validator
    when FIDO2 is enabled for a network.
    
    This ensures that when FIDO2 validation is required, the network
    also requires validator approval before users can access their passes.
    
    This matches the intended behavior: FIDO2 validate = validator approval needed
    """
    if instance.requires_fido2:
        # If FIDO2 is enabled, ensure requires_validator is also True
        if not instance.network.requires_validator:
            instance.network.requires_validator = True
            # Use update to avoid triggering other signals
            WifiNetworkLocation.objects.filter(
                pk=instance.network.pk
            ).update(requires_validator=True)
            logger.debug(f"[FIDO2] Auto-activated requires_validator for: {instance.network.name}")
    else:
        # Note: We DON'T automatically deactivate requires_validator when FIDO2 is disabled
        # This is intentional - admins may have other reason to require validation
        pass
