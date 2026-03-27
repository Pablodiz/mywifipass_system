# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

import json
import logging
import os
import base64
from datetime import timedelta

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.cache import cache
from django.utils import timezone

from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
)
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    AuthenticatorAttachment,
    AuthenticatorSelectionCriteria,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from mywifipass.models import WifiUser
from .models import PasskeyCredential

logger = logging.getLogger(__name__)

# FIDO2 Configuration - loaded from environment
_domain = os.getenv('DOMAIN', 'localhost:8000')
RP_ID = _domain.split(':')[0]
RP_NAME = 'MyWifiPass'
ssl = os.getenv('SSL', 'False').lower() in ('true', '1', 'yes')
http_header = 'https://' if ssl else 'http://'
ORIGIN = f'{http_header}{_domain}'


def bytes_to_base64url(data: bytes) -> str:
    """Convert bytes to base64url format (no padding)"""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')


def base64url_to_bytes(data: str) -> bytes:
    """Convert base64url string to bytes"""
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += '=' * padding
    return base64.urlsafe_b64decode(data)


@csrf_exempt
@require_http_methods(["POST"])
def register_start(request):
    """
    Phase 3a: Begin FIDO2 registration challenge.
    
    Request: POST /fido2/register/start/
    Body: { "email": "user@example.com" }
    
    Response: { "challenge": "...", "rp": {...}, "user": {...}, ... }
    """
    try:
        data = json.loads(request.body)
        user_email = data.get('email', '').strip()
        
        if not user_email:
            return JsonResponse({'error': 'Email required'}, status=400)
        
        try:
            wifi_user = WifiUser.objects.get(email=user_email)
        except WifiUser.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        
        # Check existing passkey
        if hasattr(wifi_user, 'passkey_credential') and wifi_user.passkey_credential.is_active:
            return JsonResponse({
                'error': 'User already has an active passkey',
                'registered_at': wifi_user.passkey_credential.created_at.isoformat()
            }, status=400)
        
        # Generate registration options
        options = generate_registration_options(
            rp_id=RP_ID,
            rp_name=RP_NAME,
            user_id=user_email.encode('utf-8'),
            user_name=user_email,
            attestation=AttestationConveyancePreference.NONE,
            authenticator_selection=AuthenticatorSelectionCriteria(
                authenticator_attachment=AuthenticatorAttachment.PLATFORM,
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.PREFERRED,
            ),
        )
        
        # Cache challenge
        cache.set(f"fido2_reg_state_{user_email}", options.challenge, timeout=300)
        logger.info(f"Registration started for {user_email}")
        
        return JsonResponse({
            'challenge': bytes_to_base64url(options.challenge),
            'rp': {'name': options.rp.name, 'id': options.rp.id},
            'user': {
                'id': bytes_to_base64url(options.user.id),
                'name': options.user.name,
                'displayName': options.user.display_name,
            },
            'pubKeyCredParams': [
                {'type': p.type, 'alg': p.alg.value} for p in options.pub_key_cred_params
            ],
            'timeout': options.timeout,
            'attestation': options.attestation,
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
    Phase 3b: Complete FIDO2 registration, store credential.
    
    Request: POST /fido2/register/finish/
    Body: { "email": "user@example.com", "credential": {...} }
    
    Response: { "success": true, "message": "Passkey registered" }
    """
    try:
        data = json.loads(request.body)
        user_email = data.get('email', '').strip()
        credential = data.get('credential')
        
        if not user_email or not credential:
            return JsonResponse({'error': 'Email and credential required'}, status=400)
        
        expected_challenge = cache.get(f"fido2_reg_state_{user_email}")
        if not expected_challenge:
            return JsonResponse({'error': 'Registration session expired'}, status=400)
        
        try:
            wifi_user = WifiUser.objects.get(email=user_email)
        except WifiUser.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        
        try:
            # Verify registration
            verified_credential = verify_registration_response(
                credential=credential,
                expected_challenge=expected_challenge,
                expected_rp_id=RP_ID,
                expected_origin=ORIGIN,
            )
            
            # Save credential
            credential_id = bytes_to_base64url(verified_credential.credential_id)
            
            if PasskeyCredential.objects.filter(credential_id=credential_id).exists():
                return JsonResponse({'error': 'Credential already registered'}, status=400)
            
            PasskeyCredential.objects.create(
                wifi_user=wifi_user,
                credential_id=credential_id,
                public_key=json.dumps({
                    'x': bytes_to_base64url(verified_credential.credential_public_key.x),
                    'y': bytes_to_base64url(verified_credential.credential_public_key.y),
                }),
                sign_count=verified_credential.sign_count,
                attestation_format=verified_credential.attestation_type,
            )
            
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
    Phase 3c: Begin FIDO2 authentication challenge.
    
    Request: POST /fido2/authenticate/start/
    Body: { "email": "user@example.com" }
    
    Response: { "challenge": "...", "allowCredentials": [...], "timeout": ... }
    """
    try:
        data = json.loads(request.body)
        user_email = data.get('email', '').strip()
        
        if not user_email:
            return JsonResponse({'error': 'Email required'}, status=400)
        
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
            # Generate authentication options
            options = generate_authentication_options(
                rp_id=RP_ID,
                user_verification=UserVerificationRequirement.REQUIRED,
                allow_credentials=[
                    {
                        'type': 'public-key',
                        'id': base64url_to_bytes(credential_obj.credential_id),
                    }
                ],
            )
            
            cache.set(f"fido2_auth_state_{user_email}", options.challenge, timeout=300)
            logger.info(f"Authentication started for {user_email}")
            
            return JsonResponse({
                'challenge': bytes_to_base64url(options.challenge),
                'timeout': options.timeout,
                'rpId': options.rp_id,
                'userVerification': options.user_verification,
                'allowCredentials': [
                    {
                        'type': cred['type'],
                        'id': bytes_to_base64url(cred['id']),
                    }
                    for cred in options.allow_credentials
                ],
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
    Phase 3d: Complete FIDO2 authentication - Acts as Admin Validator.
    
    CRITICAL: Sets allow_access_expiration = now + 3 minutes (opens CSR window)
    
    Request: POST /fido2/authenticate/finish/
    Body: { "email": "user@example.com", "credential": {...} }
    
    Response: {
        "success": true,
        "message": "CSR signing window opened (3 minutes)",
        "expires_at": "2026-03-27T14:35:42.123456Z"
    }
    """
    try:
        data = json.loads(request.body)
        user_email = data.get('email', '').strip()
        credential = data.get('credential')
        
        if not user_email or not credential:
            return JsonResponse({'error': 'Email and credential required'}, status=400)
        
        expected_challenge = cache.get(f"fido2_auth_state_{user_email}")
        if not expected_challenge:
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
            # Verify authentication
            verified_auth = verify_authentication_response(
                credential=credential,
                expected_challenge=expected_challenge,
                expected_rp_id=RP_ID,
                expected_origin=ORIGIN,
                credential_public_key=base64url_to_bytes(
                    json.loads(credential_obj.public_key).get('x', '')
                ),
                credential_id=base64url_to_bytes(credential_obj.credential_id),
                sign_count=credential_obj.sign_count,
            )
            
            # KEY PART: Open 3-minute CSR window (act as Admin Validator)
            expiration_time = timezone.now() + timedelta(minutes=3)
            wifi_user.allow_access_expiration = expiration_time
            wifi_user.save()
            
            # Update credential
            credential_obj.last_used = timezone.now()
            credential_obj.sign_count = verified_auth.new_sign_count
            credential_obj.save()
            
            cache.delete(f"fido2_auth_state_{user_email}")
            logger.info(f"Authentication successful for {user_email} - CSR window opened")
            
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
