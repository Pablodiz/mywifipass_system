# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

from django.apps import AppConfig


class Fido2PocConfig(AppConfig):
    """
    Configuration class for the FIDO2 Passkey Integration sidecar app.
    Handles WebAuthn registration and authentication as an Admin Validator.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'fido2_poc'
    verbose_name = 'FIDO2 Passkey Authentication'
    
    def ready(self):
        """Register signal handlers when the app is ready."""
        import fido2_poc.signals  # noqa: F401
