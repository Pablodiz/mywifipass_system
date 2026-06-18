# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

"""
Rate limiting (throttling) configuration for sensitive API endpoints.

Prevents abuse by limiting request rates based on IP address or user.
"""

from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class LoginAttemptThrottle(AnonRateThrottle):
    """
    Rate limit for login attempts (anonymous users).
    Applies per IP address.
    
    Limits: 5 attempts per minute, ~1000 per day
    """
    scope = 'login_attempt'


class CertificateSigningThrottle(UserRateThrottle):
    """
    Rate limit for certificate signing operations (authenticated users).
    Applies per user.
    
    Limits: 3 requests per minute
    This is conservative because CSR signing is computationally expensive.
    """
    scope = 'certificate_signing'


class AuthorizationThrottle(UserRateThrottle):
    """
    Rate limit for user authorization operations (admin users).
    Applies per admin user.
    
    Limits: 10 requests per minute
    """
    scope = 'authorization'


class DownloadThrottle(AnonRateThrottle):
    """
    Rate limit for pass/certificate downloads (anonymous users).
    Applies per IP address.
    
    Limits: 20 requests per minute
    """
    scope = 'download'


class ValidationThrottle(AnonRateThrottle):
    """
    Rate limit for user validation checks (anonymous users).
    Applies per IP address.
    
    Limits: 10 requests per minute
    """
    scope = 'validation'
