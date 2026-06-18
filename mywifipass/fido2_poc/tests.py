# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

import json
from base64 import b64encode
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from mywifipass.models import WifiUser
from .models import PasskeyCredential


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
            attestation_format='none'
        )
        self.assertIsNotNone(credential.pk)
        self.assertEqual(credential.wifi_user, self.wifi_user)
        self.assertTrue(credential.is_active)
    
    def test_passkey_onetoone_relationship(self):
        """Test: OneToOne relationship between WifiUser and PasskeyCredential."""
        credential = PasskeyCredential.objects.create(
            wifi_user=self.wifi_user,
            credential_id=b64encode(b'test_id').decode(),
            public_key=json.dumps({'x': 'x', 'y': 'y'}),
            sign_count=0
        )
        self.assertEqual(self.wifi_user.passkey_credential, credential)
    
    def test_passkey_credential_is_active_default(self):
        """Test: PasskeyCredential is_active defaults to True."""
        credential = PasskeyCredential.objects.create(
            wifi_user=self.wifi_user,
            credential_id=b64encode(b'test_id').decode(),
            public_key=json.dumps({'x': 'x', 'y': 'y'}),
            sign_count=0
        )
        self.assertTrue(credential.is_active)
    
    def test_passkey_credential_deactivation(self):
        """Test: Can deactivate a PasskeyCredential."""
        credential = PasskeyCredential.objects.create(
            wifi_user=self.wifi_user,
            credential_id=b64encode(b'test_id').decode(),
            public_key=json.dumps({'x': 'x', 'y': 'y'}),
            sign_count=0
        )
        credential.is_active = False
        credential.save()
        credential.refresh_from_db()
        self.assertFalse(credential.is_active)
    
    def test_passkey_has_timestamps(self):
        """Test: PasskeyCredential has created_at and last_used timestamps."""
        credential = PasskeyCredential.objects.create(
            wifi_user=self.wifi_user,
            credential_id=b64encode(b'test_id').decode(),
            public_key=json.dumps({'x': 'x', 'y': 'y'}),
            sign_count=0
        )
        self.assertIsNotNone(credential.created_at)
        self.assertIsNone(credential.last_used)
        
        credential.last_used = timezone.now()
        credential.save()
        credential.refresh_from_db()
        self.assertIsNotNone(credential.last_used)


@override_settings(SECURE_SSL_REDIRECT=False)
class FIDO2EndpointTestCase(TestCase):
    """
    Phase 3: Tests for FIDO2 WebAuthn endpoints.
    
    Tests the 4 primary FIDO2 endpoints:
    - register/start: Generate registration challenge
    - register/finish: Verify and store credential
    - authenticate/start: Generate authentication challenge
    - authenticate/finish: Verify authentication, open CSR window
    """
    
    def setUp(self):
        """Set up test client and test user."""
        self.client = Client(enforce_csrf_checks=False, HTTP_X_FORWARDED_PROTO="https", secure=True)
        self.test_email = 'endpoint_test@example.com'
        self.test_name = 'Endpoint Test User'
        self.test_document = 'ENDPOINT123'
        
        self.wifi_user = WifiUser.objects.create(
            email=self.test_email,
            name=self.test_name,
            id_document=self.test_document
        )
    
    # Register Start Tests
    
    def test_register_start_success(self):
        """Test: register/start endpoint returns challenge."""
        response = self.client.post(
            reverse('fido2:register_start'),
            data=json.dumps({'email': self.test_email}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('challenge', data)
        self.assertIn('rp', data)
        self.assertIn('user', data)
        self.assertIn('pubKeyCredParams', data)
    
    def test_register_start_missing_email(self):
        """Test: register/start without email returns 400."""
        response = self.client.post(
            reverse('fido2:register_start'),
            data=json.dumps({}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Email required')
    
    def test_register_start_user_not_found(self):
        """Test: register/start with non-existent user creates user and returns 200."""
        new_email = 'newuser@example.com'
        # Verify user doesn't exist
        self.assertFalse(WifiUser.objects.filter(email=new_email).exists())
        
        response = self.client.post(
            reverse('fido2:register_start'),
            data=json.dumps({'email': new_email}),
            content_type='application/json'
        )
        
        # Should succeed (200) and create user
        self.assertEqual(response.status_code, 200)
        self.assertTrue(WifiUser.objects.filter(email=new_email).exists())
        
        # Verify response has challenge
        data = response.json()
        self.assertIn('challenge', data)
        self.assertIn('rp', data)
        self.assertIn('user', data)
    
    def test_register_start_existing_passkey(self):
        """Test: register/start with existing passkey returns 400."""
        PasskeyCredential.objects.create(
            wifi_user=self.wifi_user,
            credential_id=b64encode(b'existing_id').decode(),
            public_key=json.dumps({'x': 'x', 'y': 'y'}),
            sign_count=0
        )
        response = self.client.post(
            reverse('fido2:register_start'),
            data=json.dumps({'email': self.test_email}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('already has an active passkey', response.json()['error'])
    
    # Register Finish Tests
    
    def test_register_finish_missing_email(self):
        """Test: register/finish without email returns 400."""
        response = self.client.post(
            reverse('fido2:register_finish'),
            data=json.dumps({'credential': {}}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Email and credential required')
    
    def test_register_finish_session_expired(self):
        """Test: register/finish with expired session returns 400."""
        response = self.client.post(
            reverse('fido2:register_finish'),
            data=json.dumps({
                'email': self.test_email,
                'credential': {'type': 'public-key', 'id': 'test'}
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Registration session expired')
    
    def test_register_finish_user_not_found(self):
        """Test: register/finish with non-existent user returns 400 (session validation first)."""
        response = self.client.post(
            reverse('fido2:register_finish'),
            data=json.dumps({
                'email': 'nonexistent@example.com',
                'credential': {'type': 'public-key'}
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Registration session expired')
    
    # Authenticate Start Tests
    
    def test_authenticate_start_success(self):
        """Test: authenticate/start returns challenge for registered user."""
        PasskeyCredential.objects.create(
            wifi_user=self.wifi_user,
            credential_id=b64encode(b'test_cred_id').decode(),
            public_key=json.dumps({'x': 'x', 'y': 'y'}),
            sign_count=0
        )
        response = self.client.post(
            reverse('fido2:authenticate_start'),
            data=json.dumps({'email': self.test_email}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('challenge', data)
        self.assertIn('allowCredentials', data)
    
    def test_authenticate_start_missing_email(self):
        """Test: authenticate/start without email returns 400."""
        response = self.client.post(
            reverse('fido2:authenticate_start'),
            data=json.dumps({}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Email required')
    
    def test_authenticate_start_user_not_found(self):
        """Test: authenticate/start with non-existent user returns 404."""
        response = self.client.post(
            reverse('fido2:authenticate_start'),
            data=json.dumps({'email': 'nonexistent@example.com'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['error'], 'User not found')
    
    def test_authenticate_start_no_passkey(self):
        """Test: authenticate/start without registered passkey returns 404."""
        response = self.client.post(
            reverse('fido2:authenticate_start'),
            data=json.dumps({'email': self.test_email}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn('No passkey registered', response.json()['error'])
    
    # Authenticate Finish Tests
    
    def test_authenticate_finish_missing_email(self):
        """Test: authenticate/finish without email returns 400."""
        response = self.client.post(
            reverse('fido2:authenticate_finish'),
            data=json.dumps({'credential': {}}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Email and credential required')
    
    def test_authenticate_finish_session_expired(self):
        """Test: authenticate/finish with expired session returns 400."""
        response = self.client.post(
            reverse('fido2:authenticate_finish'),
            data=json.dumps({
                'email': self.test_email,
                'credential': {'type': 'public-key', 'id': 'test'}
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Authentication session expired or challenge not found')
    
    def test_authenticate_finish_user_not_found(self):
        """Test: authenticate/finish with non-existent user returns 400 (session validation first)."""
        response = self.client.post(
            reverse('fido2:authenticate_finish'),
            data=json.dumps({
                'email': 'nonexistent@example.com',
                'credential': {'type': 'public-key'}
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Authentication session expired or challenge not found')
    
    def test_authenticate_finish_no_passkey(self):
        """Test: authenticate/finish without passkey returns 400 (session validation first)."""
        response = self.client.post(
            reverse('fido2:authenticate_finish'),
            data=json.dumps({
                'email': self.test_email,
                'credential': {'type': 'public-key'}
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Authentication session expired or challenge not found')
    
    # Invalid JSON tests
    
    def test_register_start_invalid_json(self):
        """Test: register/start with invalid JSON returns 400."""
        response = self.client.post(
            reverse('fido2:register_start'),
            data='invalid json',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid JSON', response.json()['error'])
    
    def test_register_finish_invalid_json(self):
        """Test: register/finish with invalid JSON returns 400."""
        response = self.client.post(
            reverse('fido2:register_finish'),
            data='invalid json',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid JSON', response.json()['error'])
    
    def test_authenticate_start_invalid_json(self):
        """Test: authenticate/start with invalid JSON returns 400."""
        response = self.client.post(
            reverse('fido2:authenticate_start'),
            data='invalid json',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid JSON', response.json()['error'])
    
    def test_authenticate_finish_invalid_json(self):
        """Test: authenticate/finish with invalid JSON returns 400."""
        response = self.client.post(
            reverse('fido2:authenticate_finish'),
            data='invalid json',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid JSON', response.json()['error'])


@override_settings(SECURE_SSL_REDIRECT=False)
class FIDOPageTestCase(TestCase):
    """Test suite for HTML pages serving registration/authentication UI"""

    def setUp(self):
        self.client = Client(HTTP_X_FORWARDED_PROTO="https", secure=True)

    def test_register_page_renders(self):
        """Test: /fido2/register/ returns register.html template"""
        response = self.client.get(reverse('fido2:register_page'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('Register with Passkey', response.content.decode())
        self.assertIn('registerBtn', response.content.decode())

    def test_authenticate_page_renders(self):
        """Test: /fido2/authenticate/ returns authenticate.html template"""
        response = self.client.get(reverse('fido2:authenticate_page'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('Authenticate with Passkey', response.content.decode())
        self.assertIn('authenticateBtn', response.content.decode())
