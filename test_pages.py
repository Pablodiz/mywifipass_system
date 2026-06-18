import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mywifipass.settings')

import django
django.setup()

from django.test import Client

client = Client()

# Test register page
response = client.get('/fido2/register/')
print(f"Register page status: {response.status_code}")
if response.status_code == 200:
    content = response.content.decode('utf-8', errors='ignore')
    print(f"Content starts with: {content[:100]}")
    print(f"Contains 'Authenticate with Passkey': {'Authenticate with Passkey' in content}")
    print(f"Contains 'Register with Passkey': {'Register with Passkey' in content}")

# Test authenticate page
response = client.get('/fido2/authenticate/')
print(f"\nAuthenticate page status: {response.status_code}")
if response.status_code == 200:
    content = response.content.decode('utf-8', errors='ignore')
    print(f"Content starts with: {content[:100]}")
    print(f"Contains 'Authenticate with Passkey': {'Authenticate with Passkey' in content}")
