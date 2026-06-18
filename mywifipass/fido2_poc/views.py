# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

import json
import logging
import os
import base64
import uuid
from datetime import timedelta

from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.cache import cache
from django.utils import timezone
from django.shortcuts import render

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
from .models import PasskeyCredential, AuthenticationChallenge
from .config import RP_ID, RP_NAME, ORIGIN, EXPECTED_ORIGINS

logger = logging.getLogger(__name__)


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
    Begin FIDO2 registration challenge.
    
    Request: POST /fido2/register/start/
    Body: { "email": "user@example.com" }
    
    Response: { "challenge": "...", "rp": {...}, "user": {...}, ... }
    """
    try:
        data = json.loads(request.body)
        user_email = data.get('email', '').strip()
        
        if not user_email:
            return JsonResponse({'error': 'Email required'}, status=400)
        
        # Create user if doesn't exist (allows self-registration)
        wifi_user, created = WifiUser.objects.get_or_create(
            email=user_email,
            defaults={'name': user_email.split('@')[0]}  # username from email local part
        )
        if created:
            logger.info(f"New user created during FIDO2 registration: {user_email}")
        
        # Check existing passkey
        if hasattr(wifi_user, 'passkey_credential') and wifi_user.passkey_credential.is_active:
            return JsonResponse({
                'error': 'User already has an active passkey',
                'registered_at': wifi_user.passkey_credential.created_at.isoformat()
            }, status=400)
        
        # Generate registration options
        # WebAuthn spec: user_name must not contain @ (invalid char)
        # Use UUID for user_id and sanitized email for user_name
        sanitized_username = user_email.replace('@', '.')
        
        options = generate_registration_options(
            rp_id=RP_ID,
            rp_name=RP_NAME,
            user_id=str(wifi_user.user_uuid).encode('utf-8'),  # Use UUID instead of email
            user_name=sanitized_username,  # Replace @ with . for WebAuthn compliance
            attestation=AttestationConveyancePreference.NONE,
            
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.REQUIRED,
                user_verification=UserVerificationRequirement.REQUIRED,
            ),
        )
        
        logger.info(f"FIDO2 REGISTER_START - RP_ID={RP_ID}, user_email={user_email}")
        
        # Store challenge in user session directly (supports gunicorn multi-worker without locmem issues)
        request.session[f"fido2_reg_state_{user_email}"] = bytes_to_base64url(options.challenge)
        logger.info(f"Registration started for {user_email}")
        
        # Build response with all WebAuthn options including authenticatorSelection
        response_data = {
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
            'authenticatorSelection': {
                'authenticatorAttachment': options.authenticator_selection.authenticator_attachment.value if options.authenticator_selection.authenticator_attachment else None,
                'residentKey': options.authenticator_selection.resident_key.value if options.authenticator_selection.resident_key else 'preferred',
                'userVerification': options.authenticator_selection.user_verification.value if options.authenticator_selection.user_verification else 'preferred',
            }
        }
        
        # Log the full response for debugging
        logger.info(f"FIDO2 REGISTER_START response: {response_data}")
        
        return JsonResponse(response_data)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Registration start error: {str(e)}")
        return JsonResponse({'error': 'Registration setup failed'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def register_finish(request):
    """
    Complete FIDO2 registration and store credential.
    
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
        
        expected_challenge_b64 = request.session.get(f"fido2_reg_state_{user_email}")
        if not expected_challenge_b64:
            return JsonResponse({'error': 'Registration session expired'}, status=400)
            
        expected_challenge = base64url_to_bytes(expected_challenge_b64)

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
                expected_origin=EXPECTED_ORIGINS,
            )
            
            # Save credential
            credential_id = bytes_to_base64url(verified_credential.credential_id)
            
            if PasskeyCredential.objects.filter(credential_id=credential_id).exists():
                return JsonResponse({'error': 'Credential already registered'}, status=400)
            
            PasskeyCredential.objects.create(
                wifi_user=wifi_user,
                credential_id=credential_id,
                public_key=bytes_to_base64url(verified_credential.credential_public_key),
                sign_count=verified_credential.sign_count,
                attestation_format=verified_credential.fmt,
            )
            
            request.session.pop(f"fido2_reg_state_{user_email}", None)
            logger.info(f"Registration completed for {user_email}")
            
            return JsonResponse({
                'success': True,
                'message': 'Passkey registered successfully'
            })
        except Exception as e:
            logger.error(f"Credential verification failed: {str(e)}")
            
            # Print exact challenges for debugging
            debug_info = {}
            if "challenge" in str(e).lower() or "client_data" in str(e).lower():
                try:
                    from webauthn.helpers.parse_registration_credential_json import parse_registration_credential_json
                    from webauthn.helpers.structs import CollectedClientData
                    import json as json_lib
                    
                    parsed_cred = parse_registration_credential_json(credential)
                    # Decode clientDataJSON
                    client_data_bytes = parsed_cred.response.client_data_json
                    client_data_dict = json_lib.loads(client_data_bytes.decode('utf-8'))
                    received_b64url = client_data_dict.get('challenge', '')
                    
                    debug_info = {
                        'expected_hex': expected_challenge.hex() if isinstance(expected_challenge, bytes) else str(expected_challenge),
                        'received_b64url': received_b64url,
                        'expected_b64url': bytes_to_base64url(expected_challenge) if isinstance(expected_challenge, bytes) else "",
                    }
                    logger.error(f"Challenge mismatch DEBUG: {debug_info}")
                except Exception as inner_e:
                    logger.error(f"Could not extract debug info: {inner_e}")
                    
            return JsonResponse({'error': f'Credential verification failed: {str(e)}', 'debug': debug_info}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Registration finish error: {str(e)}")
        return JsonResponse({'error': 'Registration failed'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def authenticate_start(request):
    """
    Begin FIDO2 authentication challenge.

    Supports two modes, selected automatically based on whether the client
    provides an email address:

    --- Discoverable mode (default for the Android app) ---
    Request body: {} or {"email": ""}
    The server sends allowCredentials=[] so Android Credential Manager
    presents a passkey picker to the user. A ``session_id`` UUID is generated,
    stored with the challenge, and returned to the client so it can be echoed
    back in /authenticate/finish/.

    --- Email mode (legacy, backward-compatible) ---
    Request body: {"email": "user@example.com"}
    The server looks up the user's registered credential and returns it in
    allowCredentials, bypassing the passkey picker. The challenge is keyed
    by email in the database.

    To switch the Android app back to email mode, pass ``network.user_email``
    as ``username`` in ``MainController.validateWithFido2`` instead of ``""``.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    try:
        user_email = data.get('email', '').strip()
        discoverable_mode = not bool(user_email)

        stale_time = timezone.now() - timedelta(minutes=5)

        if not discoverable_mode:
            # --- Email mode ---
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

            allow_credentials_list = [
                {
                    'type': 'public-key',
                    'id': base64url_to_bytes(credential_obj.credential_id),
                }
            ]
            # Purge stale email-mode challenges for this user
            AuthenticationChallenge.objects.filter(
                email=user_email, created_at__lt=stale_time
            ).delete()
        else:
            # --- Discoverable mode: empty allowCredentials ---
            allow_credentials_list = []
            # Purge stale discoverable challenges (session_id present, no email)
            AuthenticationChallenge.objects.filter(
                email__isnull=True, created_at__lt=stale_time
            ).delete()

        options = generate_authentication_options(
            rp_id=RP_ID,
            user_verification=UserVerificationRequirement.REQUIRED,
            allow_credentials=allow_credentials_list,
        )

        challenge_b64 = bytes_to_base64url(options.challenge)

        if not discoverable_mode:
            AuthenticationChallenge.objects.create(
                email=user_email,
                challenge=challenge_b64,
            )
            session_id_str = None
        else:
            new_session_id = uuid.uuid4()
            AuthenticationChallenge.objects.create(
                email=None,
                session_id=new_session_id,
                challenge=challenge_b64,
            )
            session_id_str = str(new_session_id)

        logger.info(
            f"Authentication started - mode={'discoverable' if discoverable_mode else 'email'}"
            + (f", user={user_email}" if not discoverable_mode else f", session={session_id_str}")
        )

        response_data = {
            'challenge': challenge_b64,
            'timeout': options.timeout,
            'rpId': options.rp_id,
            # 'preferred' instead of 'required' for Android Credential Manager compatibility
            'userVerification': 'preferred',
            'allowCredentials': [
                {
                    'type': cred['type'],
                    'id': bytes_to_base64url(cred['id']),
                    # Omitting 'transports' allows all transports (internal, hybrid, etc.)
                    # Required for Google Password Manager and cross-device passkey sync
                }
                for cred in options.allow_credentials
            ],
        }
        if session_id_str:
            response_data['session_id'] = session_id_str

        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"Authentication start error: {str(e)}")
        return JsonResponse({'error': 'Authentication setup failed'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def authenticate_finish(request):
    """
    Complete FIDO2 authentication - Acts as Admin Validator.

    CRITICAL: Sets allow_access_expiration = now + 3 minutes (opens CSR window).

    Supports two modes, matching /authenticate/start/:

    --- Discoverable mode (default for the Android app) ---
    Request body: {"session_id": "<uuid>", "credential": {...}}
    The challenge is retrieved by session_id. The authenticated user is
    identified from credential.id, which maps directly to
    PasskeyCredential.credential_id in the database - no email needed.

    --- Email mode (legacy, backward-compatible) ---
    Request body: {"email": "user@example.com", "credential": {...}}
    The challenge is retrieved by email and the user is looked up the
    same way as before.

    To switch the Android app back to email mode, pass ``network.user_email``
    as ``username`` in ``MainController.validateWithFido2`` instead of ``""``.

    Response (both modes):
    {
        "success": true,
        "message": "CSR signing window opened (3 minutes)",
        "expires_at": "2026-03-27T14:35:42.123456Z"
    }
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError as je:
        logger.error(f"JSON parsing failed: {str(je)}")
        return JsonResponse({'error': f'Invalid JSON: {str(je)}'}, status=400)

    try:
        user_email = data.get('email', '').strip()
        session_id_str = data.get('session_id', '').strip()
        credential = data.get('credential')

        if not credential:
            return JsonResponse({'error': 'Credential required'}, status=400)

        # Discoverable mode: session_id present, no email
        discoverable_mode = bool(session_id_str) and not bool(user_email)

        if not discoverable_mode and not user_email:
            return JsonResponse({'error': 'email or session_id required'}, status=400)

        # --- Resolve challenge ---
        if not discoverable_mode:
            try:
                challenge_obj = AuthenticationChallenge.objects.filter(
                    email=user_email
                ).latest('created_at')
            except AuthenticationChallenge.DoesNotExist:
                logger.warning(f"No challenge found for email {user_email}")
                return JsonResponse(
                    {'error': 'Authentication session expired or challenge not found'}, status=400
                )
        else:
            try:
                challenge_obj = AuthenticationChallenge.objects.get(session_id=session_id_str)
            except AuthenticationChallenge.DoesNotExist:
                logger.warning(f"No challenge found for session_id {session_id_str}")
                return JsonResponse({'error': 'Session not found or expired'}, status=400)

            if timezone.now() - challenge_obj.created_at > timedelta(minutes=5):
                challenge_obj.delete()
                return JsonResponse({'error': 'Session expired'}, status=400)

        expected_challenge = base64url_to_bytes(challenge_obj.challenge)

        # --- Resolve user and credential ---
        if not discoverable_mode:
            try:
                wifi_user = WifiUser.objects.get(email=user_email)
                credential_obj = PasskeyCredential.objects.get(
                    wifi_user=wifi_user,
                    is_active=True
                )
            except WifiUser.DoesNotExist:
                logger.error(f"User not found: {user_email}")
                return JsonResponse({'error': 'User not found'}, status=404)
            except PasskeyCredential.DoesNotExist:
                logger.error(f"No passkey registered for {user_email}")
                return JsonResponse({'error': 'No passkey registered'}, status=404)
        else:
            # In a WebAuthn assertion the 'id' field is the base64url-encoded
            # credential ID - the same value stored in PasskeyCredential.credential_id.
            raw_credential_id = credential.get('id') or credential.get('rawId', '')
            if not raw_credential_id:
                return JsonResponse({'error': 'Missing credential id in assertion'}, status=400)
            try:
                credential_obj = PasskeyCredential.objects.select_related('wifi_user').get(
                    credential_id=raw_credential_id,
                    is_active=True,
                )
                wifi_user = credential_obj.wifi_user
            except PasskeyCredential.DoesNotExist:
                logger.error(f"Credential not registered: {raw_credential_id}")
                return JsonResponse({'error': 'Credential not registered'}, status=404)

        # --- Verify assertion (identical for both modes) ---
        try:
            verified_auth = verify_authentication_response(
                credential=credential,
                expected_challenge=expected_challenge,
                expected_rp_id=RP_ID,
                expected_origin=EXPECTED_ORIGINS,
                credential_public_key=base64url_to_bytes(credential_obj.public_key),
                credential_current_sign_count=credential_obj.sign_count,
            )
            logger.info(f"Credential verified. New sign count: {verified_auth.new_sign_count}")

            # KEY PART: Open 3-minute CSR window (acts as Admin Validator)
            expiration_time = timezone.now() + timedelta(minutes=3)
            wifi_user.allow_access_expiration = expiration_time
            wifi_user.save()

            credential_obj.last_used = timezone.now()
            credential_obj.sign_count = verified_auth.new_sign_count
            credential_obj.save()

            # Delete the used challenge immediately (no replay possible)
            challenge_obj.delete()

            logger.info(f"Authentication successful for {wifi_user.email} - CSR window opened")
            return JsonResponse({
                'success': True,
                'message': 'CSR signing window opened (3 minutes)',
                'expires_at': expiration_time.isoformat(),
            })

        except Exception as e:
            logger.error(f"Assertion verification FAILED: {str(e)}")
            return JsonResponse({'error': f'Authentication failed: {str(e)}'}, status=400)

    except Exception as e:
        logger.error(f"Unexpected error in authenticate_finish: {str(e)}")
        return JsonResponse({'error': f'Authentication failed: {str(e)}'}, status=400)


@require_http_methods(['GET'])
def register_page(request):
    """Serve registration page with passkey registration UI"""
    return render(request, 'fido2_poc/register.html')


@require_http_methods(['GET'])
def authenticate_page(request):
    """Serve authentication page with passkey authentication UI"""
    return render(request, 'fido2_poc/authenticate.html')


@require_http_methods(['GET'])
def assetlinks_json(request):
    """
    Serve Digital Asset Links (DAL) JSON for Android app verification.
    Generated dynamically from environment variables.
    
    Required for Android Credential Manager to share passkeys between web and native app.
    
    Configuration via environment variables:
    - ANDROID_APP_PACKAGE: Android app package name (default: 'app.mywifipass')
    - ANDROID_APP_SHA256: SHA256 certificate fingerprint of the Android app
    
    Accessed by Android at: https://your-domain/.well-known/assetlinks.json
    """
    try:
        from .android_dal import get_assetlinks_data
        
        assetlinks_data = get_assetlinks_data()
        
        response = JsonResponse(
            assetlinks_data,
            safe=False,
            content_type='application/json'
        )
        response['Cache-Control'] = 'public, max-age=3600'  # Cache for 1 hour
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating assetlinks.json: {str(e)}")
        return JsonResponse({'error': 'Failed to generate asset links'}, status=500)
