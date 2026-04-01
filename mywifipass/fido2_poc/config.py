# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

"""
FIDO2 Configuration Module

This module centralizes all FIDO2-related settings, making it easy to configure
the system via environment variables without scattering configuration across views.

Environment variables:
- DOMAIN: Domain name for the FIDO2 RP (e.g., 'mywifipass.example.com')
- SSL: Whether to use HTTPS (default: 'True')
- ANDROID_ADDITIONAL_ORIGINS: Additional Android app key hashes (comma-separated)
  Format: 'android:apk-key-hash:HASH1,android:apk-key-hash:HASH2'
  These are ADDED to the official MyWifiPass app, not replacing it.

Example in .env:
    DOMAIN=mywifipass.example.com
    SSL=True
    ANDROID_ADDITIONAL_ORIGINS=android:apk-key-hash:CUSTOM_HASH1,android:apk-key-hash:CUSTOM_HASH2

The official MyWifiPass app origin is always included by default.
"""

import os
import logging

logger = logging.getLogger(__name__)


def _load_fido2_config():
    """Load and validate FIDO2 configuration from environment variables."""
    
    # RP (Relying Party) Configuration
    domain = os.getenv('DOMAIN', 'localhost:8000')
    rp_id = domain.split(':')[0]  # Extract hostname without port
    rp_name = 'MyWifiPass'
    
    # Protocol and Origin
    ssl = os.getenv('SSL', 'True').lower() in ('true', '1', 'yes')
    http_header = 'https://' if ssl else 'http://'
    origin = f'{http_header}{domain}'
    
    # Build expected origins (web + Android)
    expected_origins = [f"https://{domain}", f"http://{domain}"]
    
    # Add Android app origins
    # 1. Official MyWifiPass app (always included)
    official_mywifipass_hash = 'android:apk-key-hash:mn_EqHb9AwSF2H5gRjYnmjy7s_mRJ0DKmq4igkb2Eyo'
    expected_origins.append(official_mywifipass_hash)
    logger.info("[FIDO2] Loaded official MyWifiPass app origin (app.mywifipass)")
    
    # 2. Additional custom app origins from environment (for custom-compiled apps)
    additional_origins_str = os.getenv('ANDROID_ADDITIONAL_ORIGINS', '').strip()
    if additional_origins_str:
        # Split by comma and strip whitespace from each entry
        additional_origins = [origin.strip() for origin in additional_origins_str.split(',') if origin.strip()]
        expected_origins.extend(additional_origins)
        logger.info(f"[FIDO2] Loaded {len(additional_origins)} additional Android app origins from ANDROID_ADDITIONAL_ORIGINS")
    else:
        logger.info(
            "[FIDO2] No additional Android app origins configured (optional). "
            "To add custom-compiled app support, set ANDROID_ADDITIONAL_ORIGINS environment variable. "
            "Example: ANDROID_ADDITIONAL_ORIGINS=android:apk-key-hash:CUSTOM_HASH1,android:apk-key-hash:CUSTOM_HASH2"
        )
    
    return {
        'DOMAIN': domain,
        'RP_ID': rp_id,
        'RP_NAME': rp_name,
        'SSL': ssl,
        'ORIGIN': origin,
        'EXPECTED_ORIGINS': expected_origins,
    }


# Load configuration once at module import time
_FIDO2_CONFIG = _load_fido2_config()

# Export configuration for use in other modules
DOMAIN = _FIDO2_CONFIG['DOMAIN']
RP_ID = _FIDO2_CONFIG['RP_ID']
RP_NAME = _FIDO2_CONFIG['RP_NAME']
SSL = _FIDO2_CONFIG['SSL']
ORIGIN = _FIDO2_CONFIG['ORIGIN']
EXPECTED_ORIGINS = _FIDO2_CONFIG['EXPECTED_ORIGINS']


def log_fido2_config():
    """Log current FIDO2 configuration (for debugging)."""
    logger.info(f"FIDO2 Configuration:")
    logger.info(f"  DOMAIN: {DOMAIN}")
    logger.info(f"  RP_ID: {RP_ID}")
    logger.info(f"  RP_NAME: {RP_NAME}")
    logger.info(f"  SSL: {SSL}")
    logger.info(f"  ORIGIN: {ORIGIN}")
    logger.info(f"  EXPECTED_ORIGINS: {EXPECTED_ORIGINS}")


# Log configuration on import
log_fido2_config()
