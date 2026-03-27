# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

from django.urls import path
from . import views

app_name = 'fido2'

"""
FIDO2 Passkey Authentication Endpoints

Endpoints:
- GET  /fido2/register/     - Registration page (HTML)
- POST /fido2/register/start/ - Begin registration challenge
- POST /fido2/register/finish/ - Complete registration
- GET  /fido2/authenticate/ - Authentication page (HTML)
- POST /fido2/authenticate/start/ - Begin authentication challenge
- POST /fido2/authenticate/finish/ - Complete authentication (sets 3-min CSR window)
"""

urlpatterns = [
    # Registration pages and endpoints
    path('register/', views.register_page, name='register_page'),
    path('register/start/', views.register_start, name='register_start'),
    path('register/finish/', views.register_finish, name='register_finish'),
    
    # Authentication pages and endpoints (acts as Admin Validator)
    path('authenticate/', views.authenticate_page, name='authenticate_page'),
    path('authenticate/start/', views.authenticate_start, name='authenticate_start'),
    path('authenticate/finish/', views.authenticate_finish, name='authenticate_finish'),
]
