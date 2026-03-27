# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

from django.db import models
from mywifipass.models import WifiUser


class PasskeyCredential(models.Model):
    """
    Isolated FIDO2 passkey credential storage.
    
    This model stores WebAuthn credentials for passwordless authentication.
    It is completely isolated from core models (WifiUser, WifiNetworkLocation)
    to minimize merge conflicts in this long-lived feature branch.
    
    When a user authenticates with a passkey, the backend acts as an "Admin Validator"
    by setting allow_access_expiration = now + 3 minutes, opening a CSR signing window.
    """
    
    wifi_user = models.OneToOneField(
        WifiUser,
        on_delete=models.CASCADE,
        related_name='passkey_credential',
        help_text="Reference to the WiFi user who owns this passkey"
    )
    
    credential_id = models.CharField(
        max_length=500,
        unique=True,
        help_text="Base64-encoded FIDO2 credential ID (public, non-secret)"
    )
    
    public_key = models.TextField(
        help_text="JSON serialized JWK (Joint Web Key) public key for verification"
    )
    
    sign_count = models.IntegerField(
        default=0,
        help_text="Signature counter for replay attack detection"
    )
    
    attestation_format = models.CharField(
        max_length=50,
        default='none',
        help_text="FIDO2 attestation format (none, self, fido-u2f, packed, etc.)"
    )
    
    algorithm = models.IntegerField(
        default=-7,
        help_text="COSE algorithm identifier (ES256 = -7, more at https://www.iana.org/assignments/cose/cose.xhtml)"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the passkey was registered"
    )
    
    last_used = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last successful authentication timestamp"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this credential is currently usable for authentication"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Passkey Credential"
        verbose_name_plural = "Passkey Credentials"
    
    def __str__(self):
        return f"Passkey for {self.wifi_user.email} (registered {self.created_at.strftime('%Y-%m-%d')})"
