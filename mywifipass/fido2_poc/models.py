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


class AuthenticationChallenge(models.Model):
    """
    FIDO2 authentication challenge storage (stateless).
    
    Stores challenges for the WebAuthn authentication flow.
    These are stored in the database (not HTTP sessions) to avoid
    session persistence issues with mobile clients.
    
    Challenge lifecycle:
    1. /authenticate/start/ → Creates entry with email + challenge
    2. /authenticate/finish/ → Retrieves challenge by email + validates
    3. Auto-deleted after 5 minutes (via created_at)
    """
    
    email = models.EmailField(
        help_text="User email requesting authentication"
    )
    
    challenge = models.TextField(
        help_text="Base64-encoded WebAuthn challenge (non-secret, unique per request)"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Challenge creation timestamp"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Authentication Challenge"
        verbose_name_plural = "Authentication Challenges"
        # Only one active challenge per email at a time
        unique_together = [('email', 'created_at')]
        # Auto-cleanup: challenges older than 5 minutes are stale
        indexes = [
            models.Index(fields=['email', '-created_at']),
        ]
    
    def __str__(self):
        return f"Challenge for {self.email} (created {self.created_at.strftime('%Y-%m-%d %H:%M:%S')})"


from mywifipass.models import WifiNetworkLocation

class Fido2NetworkConfig(models.Model):
    """
    Sidecar configuration to determine if a network requires FIDO2 validation.
    Instead of modifying the core WifiNetworkLocation directly, this model
    extends its functionality using a OneToOne relationship.
    """
    network = models.OneToOneField(
        WifiNetworkLocation,
        on_delete=models.CASCADE,
        related_name='fido2_config',
        help_text="The network this FIDO2 configuration applies to."
    )
    
    requires_fido2 = models.BooleanField(
        default=False,
        help_text="If True, users must validate their passes using a FIDO2 passkey via the app."
    )

    class Meta:
        verbose_name = "FIDO2 Network Config"
        verbose_name_plural = "FIDO2 Network Configs"

    def __str__(self):
        status = "Required" if self.requires_fido2 else "Optional"
        return f"FIDO2 Config for {self.network.name} ({status})"
