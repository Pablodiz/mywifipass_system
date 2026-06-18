# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

"""
Android Digital Asset Links Configuration

This module manages the Android Digital Asset Links (DAL) which enables
seamless FIDO2 credential sharing between web and native app.

Configuration via environment variables:
- ANDROID_ADDITIONAL_APPS: Additional Android apps (JSON format, semi-optional)
  Format: '[{"package_name":"com.custom.app","sha256":"XX:XX:..."}]'
  These are ADDED to the official MyWifiPass app, not replacing it.

Example in .env:
    ANDROID_ADDITIONAL_APPS=[{"package_name":"com.mycompany.mywifipass","sha256":"AA:BB:CC:..."}]

The official MyWifiPass app is always included by default:
    - package_name: app.mywifipass
    - sha256: 9A:7F:C4:A8:76:FD:03:04:85:D8:7E:60:46:36:27:9A:3C:BB:B3:F9:91:27:40:CA:9A:AE:22:82:46:F6:13:2A

To get the SHA256 from your Android app keystore:
    keytool -list -v -keystore your_keystore.jks -alias your_key_alias
"""

import os
import logging
import json

logger = logging.getLogger(__name__)


def _load_android_apps():
    """
    Load Android apps configuration from environment variables.
    
    Returns:
        list: List of app configs, each with 'package_name' and 'sha256_cert_fingerprints'
    """
    
    apps = []
    
    # 1. Official MyWifiPass app (always included).
    # Both release and debug fingerprints are listed so the app works when run
    # directly from Android Studio (debug key) as well as from a signed release build.
    #
    # Release key: mi-release-key.jks (alias: pablo)
    #   keytool -list -v -keystore mi-release-key.jks -alias pablo
    # Debug key:   ~/.android/debug.keystore (alias: androiddebugkey)
    #   keytool -list -v -keystore ~/.android/debug.keystore -alias androiddebugkey -storepass android
    official_app = {
        'package_name': 'app.mywifipass',
        'sha256_cert_fingerprints': [
            '22:E6:53:4A:E9:6D:39:96:C2:E5:0B:7A:36:17:54:82:7B:FD:50:07:21:0C:BD:EA:5F:AF:3E:D1:68:EE:88:0E',  # release
            '9A:7F:C4:A8:76:FD:03:04:85:D8:7E:60:46:36:27:9A:3C:BB:B3:F9:91:27:40:CA:9A:AE:22:82:46:F6:13:2A',  # debug
        ]
    }
    apps.append(official_app)
    logger.info("[Android DAL] Loaded official MyWifiPass app (app.mywifipass)")
    
    # 2. Additional custom apps from environment (for custom-compiled apps)
    additional_apps_json = os.getenv('ANDROID_ADDITIONAL_APPS', '').strip()
    if additional_apps_json:
        try:
            additional_apps_list = json.loads(additional_apps_json)
            if not isinstance(additional_apps_list, list):
                additional_apps_list = [additional_apps_list]
            
            for app_config in additional_apps_list:
                if isinstance(app_config, dict):
                    package_name = app_config.get('package_name')
                    sha256 = app_config.get('sha256')
                    
                    if package_name and sha256:
                        apps.append({
                            'package_name': package_name,
                            'sha256_cert_fingerprints': [sha256]
                        })
                        logger.info(f"[Android DAL] Loaded additional app: {package_name}")
                    else:
                        logger.warning(f"[Android DAL] Invalid app config (missing package_name or sha256): {app_config}")
            
            logger.info(f"[Android DAL] Total apps configured: {len(apps)} (1 official + {len(apps)-1} custom)")
        except json.JSONDecodeError as e:
            logger.error(f"[Android DAL] Failed to parse ANDROID_ADDITIONAL_APPS JSON: {str(e)}")
            logger.info("[Android DAL] Using only official app. Check ANDROID_ADDITIONAL_APPS format.")
    else:
        logger.info(
            "[Android DAL] No additional Android apps configured (optional). "
            "To add custom-compiled app support, set ANDROID_ADDITIONAL_APPS environment variable. "
            "Example: ANDROID_ADDITIONAL_APPS='[{\"package_name\":\"com.custom.app\",\"sha256\":\"AA:BB:CC:...\"}]'"
        )
    
    return apps


def get_assetlinks_data():
    """
    Generate Digital Asset Links JSON for Android app verification.
    
    Returns:
        list: DAL configuration for GET /.well-known/assetlinks.json
    """
    apps = _load_android_apps()
    
    assetlinks = []
    for app in apps:
        assetlinks.append({
            "relation": [
                "delegate_permission/common.handle_all_urls",
                "delegate_permission/common.get_login_creds"
            ],
            "target": {
                "namespace": "android_app",
                "package_name": app['package_name'],
                "sha256_cert_fingerprints": app['sha256_cert_fingerprints']
            }
        })
    
    return assetlinks
