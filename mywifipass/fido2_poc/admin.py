# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

from django.contrib import admin
from mywifipass.models import WifiNetworkLocation
from .models import PasskeyCredential, Fido2NetworkConfig


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


class Fido2NetworkConfigInline(admin.TabularInline):
    """
    Inline admin for FIDO2 network configuration.
    Allows toggling FIDO2 requirement directly from the network edit page.
    """
    model = Fido2NetworkConfig
    fields = ('requires_fido2',)
    extra = 1  # Allow adding a new config if it doesn't exist
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        """Allow manual addition; creates the missing config if needed."""
        return True


# Import the existing WifiNetworkLocationAdmin to extend it
try:
    from mywifipass.admin import WifiNetworkLocationAdmin as OriginalNetworkAdmin
    
    class WifiNetworkLocationWithFido2Admin(OriginalNetworkAdmin):
        """
        Extended admin for WifiNetworkLocation that includes FIDO2 configuration.
        Integrates FIDO2 settings directly into the network edit page.
        """
        # Add Fido2NetworkConfigInline to existing inlines
        inlines = list(getattr(OriginalNetworkAdmin, 'inlines', [])) + [Fido2NetworkConfigInline]

        class Media:
            js = ('fido2_poc/admin/fido2_requires_validator_lock.js',)
    
    # Unregister the original admin and re-register with FIDO2 support
    admin.site.unregister(WifiNetworkLocation)
    admin.site.register(WifiNetworkLocation, WifiNetworkLocationWithFido2Admin)
    
except Exception as e:
    print(f"[FIDO2 Admin Warning] Could not extend WifiNetworkLocationAdmin: {e}")
    print("Registering Fido2NetworkConfig as standalone admin instead")
    
    @admin.register(Fido2NetworkConfig)
    class Fido2NetworkConfigAdmin(admin.ModelAdmin):
        list_display = ('network', 'requires_fido2')
        list_filter = ('requires_fido2',)
        search_fields = ('network__name', 'network__SSID')
