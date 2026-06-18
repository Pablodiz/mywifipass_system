# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

"""
FIDO2 API Extensions

This module provides serializers and endpoints for FIDO2 configuration
without modifying the core mywifipass app.
"""

from rest_framework import serializers
from mywifipass.models import WifiNetworkLocation
from .models import Fido2NetworkConfig


class WifiNetworkLocationFido2Serializer(serializers.ModelSerializer):
    """
    Extended serializer for WifiNetworkLocation that includes FIDO2 configuration.
    
    This is meant to be used ONLY by the admin/extended API, not the core API.
    It allows reading and writing FIDO2 settings without modifying the core serializer.
    """
    requires_fido2_validation = serializers.SerializerMethodField()

    class Meta:
        model = WifiNetworkLocation
        fields = [
            'name', 'SSID',
            'location', 'description', 'brief_description', 'start_date', 'end_date', 
            'form_link', 'is_registration_open', 'is_enabled_in_radius', 
            'is_visible_in_web', 'requires_validator', 'send_emails_automatically', 'logo', 'location_uuid',
            'requires_fido2_validation'
        ]
        extra_kwargs = {
            'location_uuid': {'read_only': True},
        }

    def get_requires_fido2_validation(self, obj):
        """Check if the network requires FIDO2 validation for accessing passes."""
        try:
            return obj.fido2_config.requires_fido2
        except Exception:
            return False
