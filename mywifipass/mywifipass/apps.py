# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

from django.apps import AppConfig


class MywifipassConfig(AppConfig):
    """
    Configuration class for the MyWifiPass Django app.
    Registers signal handlers for security-related events.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mywifipass'
    
    def ready(self):
        """
        Import signal handlers when app is ready.
        This ensures our security signals are registered.
        """
        import mywifipass.signals  # noqa: F401
