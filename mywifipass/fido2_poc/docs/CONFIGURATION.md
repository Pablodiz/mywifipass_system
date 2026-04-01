# FIDO2 Configuration

## Environment Variables

Add these to `.env`:

### Optional: Add Custom Android Apps

```bash
# Method 1: Add app origins directly (if package name doesn't matter)
ANDROID_ADDITIONAL_ORIGINS=android:apk-key-hash:HASH1,android:apk-key-hash:HASH2

# Method 2: Add complete app configs with package names (recommended)
ANDROID_ADDITIONAL_APPS=[
  {"package_name":"com.mycompany.mywifipass","sha256":"HASH1"},
  {"package_name":"com.mycompany.mywifipass.beta","sha256":"HASH2"}
]
```

Note: The official MyWifiPass app (`app.mywifipass`) is always included.

## Getting SHA256 Certificate Hash

Extract from your Android app keystore:

```bash
keytool -list -v -keystore your_keystore.jks -alias your_key_alias -storepass password
```

Look for the SHA256 line. Format should be: `XX:XX:XX:...` (with colons).

## How It Works

1. **config.py** - Loads FIDO2 configuration from environment
2. **android_dal.py** - Generates Digital Asset Links JSON dynamically
3. **views.py** - Serves assetlinks.json at `GET /.well-known/assetlinks.json`
4. **signals.py** - Auto-activates `requires_validator` when FIDO2 enabled
5. **admin.py** - Shows FIDO2 config checkbox in network admin interface

## Docker Deployment

Changes to `ANDROID_ADDITIONAL_APPS` take effect immediately on container restart:

```bash
# Update .env, then:
docker compose restart mywifipass-app
```

Verify assetlinks.json is generated:
```bash
curl https://your-domain/.well-known/assetlinks.json | jq .
```

## Admin Interface

Navigate to Django Admin → WiFi Networks:

- New network: FIDO2 Config section appears automatically
- Check "Requires FIDO2" to enable
- `requires_validator` activates automatically when FIDO2 is enabled
