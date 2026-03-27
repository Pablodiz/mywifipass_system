# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

from django.test import TestCase
from mywifipass.models import WifiUser
from .models import PasskeyCredential
import json
from base64 import b64encode


class PasskeyCredentialModelTestCase(TestCase):
    """
    Phase 2: Tests for PasskeyCredential model isolation.
    
    Verifies that the isolated PasskeyCredential model:
    - Stores FIDO2 credentials securely
    - Maintains OneToOne relationship with WifiUser
    - Doesn't impact core WiFi provisioning models
    """
    
    def setUp(self):
        """Create test WiFi user and related objects."""
        self.test_email = 'fido2test@example.com'
        self.test_name = 'FIDO2 Test User'
        self.test_document = 'DOC123456'
        
        self.wifi_user = WifiUser.objects.create(
            email=self.test_email,
            name=self.test_name,
            id_document=self.test_document
        )
    
    def test_wifiuser_created(self):
        """Verify test WiFi user was created successfully."""
        self.assertIsNotNone(self.wifi_user.user_uuid)
        self.assertEqual(self.wifi_user.email, self.test_email)
        self.assertEqual(self.wifi_user.name, self.test_name)
    
    def test_passkey_credential_creation(self):
        """Test: Can create a PasskeyCredential for WiFi user."""
        credential = PasskeyCredential.objects.create(
            wifi_user=self.wifi_user,
            credential_id=b64encode(b'test_credential_id').decode(),
            public_key=json.dumps({
                'x': b64encode(b'test_x_coord').decode(),
                'y': b64encode(b'test_y_coord').decode(),
            }),
            sign_count=0,
            attestation_format='none',
            algorithm=-7  # ES256
        )
        
        self.assertIsNotNone(credential.id)
        self.assertEqual(credential.wifi_user, self.wifi_user)
        self.assertTrue(credential.is_active)
    
    def test_passkey_onetoone_relationship(self):
        """Test: WiFi user can have exactly one passkey."""
        PasskeyCredential.objects.create(
            wifi_user=self.wifi_user,
            credential_id=b64encode(b'cred_1').decode(),
            public_key='{"x": "...", "y": "..."}',
        )
        
        # Verify relationship
        self.assertEqual(
            PasskeyCredential.objects.get(wifi_user=self.wifi_user),
            self.wifi_user.passkey_credential
        )
    
    def test_passkey_credential_fields(self):
        """Test: PasskeyCredential stores all required FIDO2 fields."""
        credential = PasskeyCredential.objects.create(
            wifi_user=self.wifi_user,
            credential_id='dGVzdF9jcmVk',  # Base64
            public_key='{"x": "abc", "y": "def"}',
            sign_count=5,
            attestation_format='fido-u2f',
            algorithm=-7
        )
        
        self.assertEqual(credential.credential_id, 'dGVzdF9jcmVk')
        self.assertEqual(credential.sign_count, 5)
        self.assertEqual(credential.attestation_format, 'fido-u2f')
        self.assertEqual(credential.algorithm, -7)
    
    def test_passkey_active_inactive(self):
        """Test: PasskeyCredential can be deactivated."""
        credential = PasskeyCredential.objects.create(
            wifi_user=self.wifi_user,
            credential_id='cred_active',
            public_key='{}',
            is_active=True
        )
        
        self.assertTrue(credential.is_active)
        
        # Deactivate
        credential.is_active = False
        credential.save()
        
        credential.refresh_from_db()
        self.assertFalse(credential.is_active)
    
    def test_passkey_isolation_from_core_models(self):
        """Test: PasskeyCredential doesn't affect WifiUser core fields."""
        # Create passkey without modifying WifiUser
        PasskeyCredential.objects.create(
            wifi_user=self.wifi_user,
            credential_id='isolated_cred',
            public_key='{}',
        )
        
        # WifiUser should be completely unchanged
        self.wifi_user.refresh_from_db()
        self.assertEqual(self.wifi_user.email, self.test_email)
        # No side effects on core provisioning fields
    
    def test_admin_interface_registered(self):
        """Test: PasskeyCredential model is registered in Django admin."""
        from django.contrib import admin
        from .admin import PasskeyCredentialAdmin
        
        # Verify admin is registered
        self.assertTrue(
            admin.site.is_registered(PasskeyCredential),
            "PasskeyCredential should be registered in admin"
        )
