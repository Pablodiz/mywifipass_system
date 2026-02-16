# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

from django import forms
from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError
import re
from mywifipass.models import WifiUser, WifiNetworkLocation


def validate_email_header_injection(email: str):
    """
    Validate that email address doesn't contain header injection characters.
    
    SECURITY: Prevents SMTP header injection attacks (e.g., newlines, carriage returns)
    by rejecting emails with suspicious characters that could inject headers like Bcc, Cc, etc.
    """
    suspicious_chars = ['\n', '\r', '\t', '%0a', '%0d']
    email_lower = email.lower()
    
    for char in suspicious_chars:
        if char in email_lower:
            raise ValidationError(
                "Email address contains invalid characters that could be used for header injection."
            )
    
    # Also check for common injection patterns
    if re.search(r'(?:bcc|cc|subject|to):', email, re.IGNORECASE):
        raise ValidationError(
            "Email address contains suspicious patterns that could indicate header injection."
        )


class WifiUserForm(forms.ModelForm):
    """Form for registering WiFi users with email validation."""
    
    email = forms.EmailField(
        validators=[
            EmailValidator(),
            validate_email_header_injection,
        ],
        help_text="Valid email address (used for receiving WiFi pass)"
    )
    
    class Meta:
        model = WifiUser
        fields = ["name", "email", "id_document"]
    
    def clean_email(self):
        """
        Additional email validation and sanitization.
        
        SECURITY: Ensures email is clean and safe before saving.
        """
        email = self.cleaned_data.get('email')
        
        if email:
            # Strip whitespace
            email = email.strip().lower()
            
            # Validate length
            if len(email) > 254:  # RFC 5321
                raise ValidationError("Email address is too long.")
            
            # Check for duplicate emails in same network
            if self.instance.pk:
                # Update case: check for duplicates excluding current user
                duplicate = WifiUser.objects.filter(
                    email=email,
                    wifiLocation=self.instance.wifiLocation
                ).exclude(user_uuid=self.instance.user_uuid).exists()
            else:
                # Create case: check for duplicates in the network
                network = self.initial.get('wifiLocation') or getattr(self, 'network', None)
                if network:
                    duplicate = WifiUser.objects.filter(
                        email=email,
                        wifiLocation=network
                    ).exists()
                else:
                    duplicate = False
            
            if duplicate:
                raise ValidationError(
                    "Email already registered in this network."
                )
        
        return email
    
    def clean_name(self):
        """Sanitize name field."""
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
            if len(name) < 2:
                raise ValidationError("Name must be at least 2 characters.")
            if len(name) > 64:
                raise ValidationError("Name cannot exceed 64 characters.")
        return name


class CSVImportForm(forms.Form):
    """Form for bulk importing WiFi users from CSV."""
    
    wifiLocation = forms.ChoiceField(
        label="Select Wifi Location",
        choices=[("", "--SELECT A WIFI LOCATION--")],
    )

    csv_file = forms.FileField(
        label="Select CSV File", 
        help_text="Upload a CSV file with columns: name, email, id_document",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate the choices for the wifiLocation field dynamically
        self.fields['wifiLocation'].choices += WifiNetworkLocation.objects.values_list('pk', 'name')
    
    def clean_csv_file(self):
        """
        Validate CSV file size and format.
        
        SECURITY: Prevent DoS via large file uploads.
        """
        csv_file = self.cleaned_data.get('csv_file')
        
        if csv_file:
            # Check file size (max 5MB for CSV)
            if csv_file.size > 5 * 1024 * 1024:
                raise ValidationError("CSV file is too large (max 5MB).")
            
            # Check file extension
            if not csv_file.name.endswith('.csv'):
                raise ValidationError("File must be a CSV file (.csv extension).")
        
        return csv_file
