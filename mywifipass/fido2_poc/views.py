# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

import json
import logging
import os
from base64 import b64encode, b64decode
from datetime import timedelta

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings

from fido2.server import Fido2Server
from fido2.webauthn import PublicKeyCredentialRpEntity

from mywifipass.models import WifiUser
from .models import PasskeyCredential

logger = logging.getLogger(__name__)

# FIDO2 Configuration - loaded from environment (same as settings.py)
# RP_ID: Relying Party Identifier (domain without scheme or port)
# Example: 'mywifipass.com' from DOMAIN='mywifipass.com' or 'mywifipass.com:8000'
_domain = os.getenv('DOMAIN', 'localhost:8000')
RP_ID = _domain.split(':')[0]  # Remove port if present
RP_NAME = 'MyWifiPass'

# ORIGIN: Full URL origin for WebAuthn verification
# Example: 'https://mywifipass.com' or 'http://localhost:8000'
ssl = os.getenv('SSL', 'False').lower() in ('true', '1', 'yes')
http_header = 'https://' if ssl else 'http://'
ORIGIN = f'{http_header}{_domain}'

# Initialize FIDO2 server
rp = PublicKeyCredentialRpEntity(RP_ID, RP_NAME)
server = Fido2Server(rp)


@csrf_exempt
@require_http_methods(["POST"])
def register_start(request):
    """
    Phase 3a: Begin FIDO2 registration - return challenge.
    
    Request: POST /fido2/register/start/
    Body: { "email": "user@example.com" }
    
    Response: { "challenge": "...", "rp": {...}, "user": {...}, ... }
    """
    try:
        data = json.loads(request.body)
        user_email = data.get('email', '').strip()
        
        if not user_email:
            return JsonResponse({'error': 'Email required'}, status=400)
        
        # Get user
        try:
            wifi_user = WifiUser.objects.get(email=user_email)
        except WifiUser.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        
        # Check if user already has an active passkey
        if hasattr(wifi_user, 'passkey_credential') and wifi_user.passkey_credential.is_active:
            return JsonResponse({
                'error': 'User already has an active passkey',
                'registered_at': wifi_user.passkey_credential.created_at.isoformat()
            }, status=400)
        
        # Generate registration challenge
        registration_data, state = server.register_begin(
            {
                'id': user_email.encode('utf-8'),
                'name': user_email,
                'display_name': wifi_user.name or user_email
            }
        )
        
        # Store state in cache (5 min timeout)
        cache.set(f"fido2_reg_state_{user_email}", state, timeout=300)
        
        logger.info(f"Registration started for {user_email}")
        
        return JsonResponse({
            'challenge': b64encode(registration_data['publicKey']['challenge']).decode('utf-8'),
            'rp': registration_data['publicKey']['rp'],
            'user': registration_data['publicKey']['user'],
            'pubKeyCredParams': registration_data['publicKey']['pubKeyCredParams'],
            'timeout': registration_data['publicKey']['timeout'],
            'attestation': registration_data['publicKey'].get('attestation', 'none'),
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Registration start error: {str(e)}")
        return JsonResponse({'error': 'Registration setup failed'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def register_finish(request):
    """
    Phase 3b: Complete FIDO2 registration - store credential.
    
    Request: POST /fido2/register/finish/
    Body: { "email": "user@example.com", "credential_json": {...} }
    
    Response: { "success": true, "message": "Passkey registered" }
    """
    try:
        data = json.loads(request.body)
        user_email = data.get('email', '').strip()
        credential_json = data.get('credential_json')
        
        if not user_email or not credential_json:
            return JsonResponse({'error': 'Email and credential required'}, status=400)
        
        # Retrieve cached state
        state = cache.get(f"fido2_reg_state_{user_email}")
        if not state:
            return JsonResponse({'error': 'Registration session expired'}, status=400)
        
        try:
            wifi_user = WifiUser.objects.get(email=user_email)
        except WifiUser.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        
        try:
            # Decode credential response
            attestation_object = b64decode(credential_json['response']['attestationObject'])
            client_data_json = b64decode(credential_json['response']['clientDataJSON'])
            
            # Complete registration (verify attestation)
            auth_data = server.register_complete(state, attestation_object, client_data_json)
            
            # Store credential
            credential_id = b64encode(auth_data.credential_data.credential_id).decode('utf-8')
            
            # Check if credential already exists
            existing = PasskeyCredential.objects.filter(credential_id=credential_id).first()
            if existing:
                return JsonResponse({'error': 'Credential already registered'}, status=400)
            
            PasskeyCredential.objects.create(
                wifi_user=wifi_user,
                credential_id=credential_id,
                public_key=json.dumps({
                    'x': b64encode(auth_data.credential_data.credential_public_key.x).decode('utf-8'),
                    'y': b64encode(auth_data.credential_data.credential_public_key.y).decode('utf-8'),
                }),
                sign_count=auth_data.sign_count,
                attestation_format=auth_data.fmt,
            )
            
            # Clean up cache
            cache.delete(f"fido2_reg_state_{user_email}")
            
            logger.info(f"Registration completed for {user_email}")
            
            return JsonResponse({
                'success': True,
                'message': 'Passkey registered successfully'
            })
        except Exception as e:
            logger.error(f"Credential verification failed: {str(e)}")
            return JsonResponse({'error': f'Credential verification failed: {str(e)}'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Registration finish error: {str(e)}")
        return JsonResponse({'error': 'Registration failed'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def authenticate_start(request):
    """
    Phase 3c: Begin FIDO2 authentication - return challenge.
    
    Request: POST /fido2/authenticate/start/
    Body: { "email": "user@example.com" }
    
    Response: { "challenge": "...", "allowCredentials": [...], "timeout": ... }
    """
    try:
        data = json.loads(request.body)
        user_email = data.get('email', '').strip()
        
        if not user_email:
            return JsonResponse({'error': 'Email required'}, status=400)
        
        # Get user and credential
        try:
            wifi_user = WifiUser.objects.get(email=user_email)
            credential_obj = PasskeyCredential.objects.get(
                wifi_user=wifi_user,
                is_active=True
            )
        except WifiUser.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        except PasskeyCredential.DoesNotExist:
            return JsonResponse({'error': 'No passkey registered for this user'}, status=404)
        
        try:
            # Generate authentication challenge
            authentication_data, state = server.authenticate_begin(
                [{'id': b64decode(credential_obj.credential_id), 'type': 'public-key'}]
            )
            
            # Store state in cache (5 min timeout)
            cache.set(f"fido2_auth_state_{user_email}", state, timeout=300)
            
            logger.info(f"Authentication started for {user_email}")
            
            return JsonResponse({
                'challenge': b64encode(authentication_data['publicKey']['challenge']).decode('utf-8'),
                'timeout': authentication_data['publicKey']['timeout'],
                'allowCredentials': authentication_data['publicKey'].get('allowCredentials', []),
            })
        except Exception as e:
            logger.error(f"Authentication setup error: {str(e)}")
            return JsonResponse({'error': 'Authentication setup failed'}, status=500)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Authentication start error: {str(e)}")
        return JsonResponse({'error': 'Authentication setup failed'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def authenticate_finish(request):
    """
    Phase 3d: Complete FIDO2 authentication - ACTS AS ADMIN VALIDATOR.
    
    CRITICAL: Sets allow_access_expiration = now + 3 minutes
    This acts like the user just was validated by Admin, opening CSR signing window.
    
    Request: POST /fido2/authenticate/finish/
    Body: { "email": "user@example.com", "assertion_json": {...} }
    
    Response: {
        "success": true,
        "message": "CSR signing window opened (3 minutes)",
        "expires_at": "2026-03-27T14:35:42.123456Z"
    }
    """
    try:
        data = json.loads(request.body)
        user_email = data.get('email', '').strip()
        assertion_json = data.get('assertion_json')
        
        if not user_email or not assertion_json:
            return JsonResponse({'error': 'Email and assertion required'}, status=400)
        
        # Retrieve cached state
        state = cache.get(f"fido2_auth_state_{user_email}")
        if not state:
            return JsonResponse({'error': 'Authentication session expired'}, status=400)
        
        try:
            wifi_user = WifiUser.objects.get(email=user_email)
            credential_obj = PasskeyCredential.objects.get(
                wifi_user=wifi_user,
                is_active=True
            )
        except WifiUser.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        except PasskeyCredential.DoesNotExist:
            return JsonResponse({'error': 'No passkey registered'}, status=404)
        
        try:
            # Decode assertion response
            authenticator_data = b64decode(assertion_json['response']['authenticatorData'])
            client_data_json = b64decode(assertion_json['response']['clientDataJSON'])
            signature = b64decode(assertion_json['response']['signature'])
            
            # Complete authentication (verify signature)
            auth_data = server.authenticate_complete(
                state,
                [{'id': b64decode(credential_obj.credential_id), 'type': 'public-key'}],
                authenticator_data,
                client_data_json,
                signature
            )
            
            # ⭐⭐⭐ THE KEY PART: Act as Admin Validator ⭐⭐⭐
            # Open 3-minute CSR signing window
            expiration_time = timezone.now() + timedelta(minutes=3)
            wifi_user.allow_access_expiration = expiration_time
            wifi_user.save()
            
            # Update credential metadata
            credential_obj.last_used = timezone.now()
            credential_obj.sign_count = auth_data.sign_count
            credential_obj.save()
            
            # Clean up cache
            cache.delete(f"fido2_auth_state_{user_email}")
            
            logger.info(f"Authentication successful for {user_email} - CSR window opened until {expiration_time}")
            
            return JsonResponse({
                'success': True,
                'message': 'CSR signing window opened (3 minutes)',
                'expires_at': expiration_time.isoformat()
            })
        except Exception as e:
            logger.error(f"Assertion verification failed: {str(e)}")
            return JsonResponse({'error': f'Authentication failed: {str(e)}'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Authentication finish error: {str(e)}")
        return JsonResponse({'error': 'Authentication failed'}, status=500)
