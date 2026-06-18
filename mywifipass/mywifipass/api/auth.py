# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

import logging
from django.shortcuts import get_object_or_404
from django.http import Http404
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from mywifipass.api.auth_model import User, LoginToken
from mywifipass.api.throttles import LoginAttemptThrottle

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([LoginAttemptThrottle])
def obtain_auth_token_username_token(request):
    """
    Obtains an authentication token using username and QR token.
    
    SECURITY: This endpoint accepts POST requests that contain authentication credentials
    (username + token from QR code). It should only be called via TokenAuthentication
    (stateless API calls) and not via SessionAuthentication (browser cookies).
    
    To prevent CSRF attacks, clients must:
    1. Use the API token in Authorization header (preferred)
    2. Include valid CSRF token if using session-based auth (not recommended for APIs)
    
    Args:
        request: HTTP request with POST data containing 'username' and 'token'
    
    Returns:
        Response with DiagnosticInfo token or error
    """
    try:
        username = request.data.get('username')
        qr_token = request.data.get('token')
        if not username or not qr_token:
            return Response({'error': 'username and token are required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = get_object_or_404(User, username=username)
        except Http404:
            return Response({'error': f'User with username {username} not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            token = get_object_or_404(LoginToken, token=qr_token, user=user)
            if token.is_valid():
                auth_token, created = Token.objects.get_or_create(user=user)
                return Response({'token': str(auth_token)}, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Token is expired.'}, status=status.HTTP_400_BAD_REQUEST)
        except Http404:
            return Response({'error': f'Token {qr_token} not found for user {username}.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        # Log full exception for debugging, but don't expose it to client
        logger.exception(f"Unexpected error in obtain_auth_token_username_token: {type(e).__name__}")
        return Response(
            {'error': 'Authentication failed. Please try again.'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )