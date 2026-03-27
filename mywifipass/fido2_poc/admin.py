# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

from django.contrib import admin
from .models import PasskeyCredential


@admin.register(PasskeyCredential)
class PasskeyCredentialAdmin(admin.ModelAdmin):
    """
    Django Admin interface for FIDO2 passkey credentials.
    Allows admins to view, manage, and revoke user passkeys.
    """
    
    list_display = ('wifi_user_email', 'created_at', 'last_used', 'is_active', 'sign_count')
    list_filter = ('is_active', 'created_at', 'attestation_format')
    search_fields = ('wifi_user__email', 'credential_id')
    readonly_fields = ('created_at', 'last_used', 'credential_id', 'public_key', 'sign_count')
    
    fieldsets = (
        ('User & Credential', {
            'fields': ('wifi_user', 'credential_id', 'is_active')
        }),
        ('Security Details', {
            'fields': ('public_key', 'algorithm', 'attestation_format', 'sign_count'),
            'classes': ('collapse',)
        }),
        ('Timeline', {
            'fields': ('created_at', 'last_used'),
            'classes': ('collapse',)
        }),
    )
    
    def wifi_user_email(self, obj):
        """Display the associated WiFi user's email."""
        return obj.wifi_user.email
    wifi_user_email.short_description = 'User Email'
    wifi_user_email.admin_order_field = 'wifi_user__email'
    
    def has_add_permission(self, request):
        """Disable manual credential creation via admin (created via WebAuthn only)."""
        return False
