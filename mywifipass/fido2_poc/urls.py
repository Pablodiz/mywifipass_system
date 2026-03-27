# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

from django.urls import path
from . import views

app_name = 'fido2'

"""
FIDO2 Passkey Authentication Endpoints

Phase 1: URL routing structure ready
Phase 3+: Endpoints will be implemented in views.py

Endpoints to implement:
- POST /fido2/register/start/ - Begin registration challenge
- POST /fido2/register/finish/ - Complete registration
- POST /fido2/authenticate/start/ - Begin authentication challenge
- POST /fido2/authenticate/finish/ - Complete authentication (sets 3-min CSR window)
"""

urlpatterns = [
    # To be added in Phase 3
]
