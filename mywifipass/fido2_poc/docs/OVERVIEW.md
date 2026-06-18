# FIDO2 PoC - Overview

This is a proof-of-concept implementation of FIDO2 passkey authentication. It's contained entirely within `fido2_poc/` and doesn't modify the core `mywifipass/` app.

## Architecture

### Components

- **config.py** - Central configuration loading from environment
- **android_dal.py** - Dynamic Digital Asset Links generation
- **models.py** 
  - `PasskeyCredential`: Stores public keys for registered users.
  - `AuthenticationChallenge`: *Stateless* table to store WebAuthn challenges linked to emails. Has a 5-minute auto-expiry ensuring resilience in high-concurrency environments or load-balanced deployments.
  - `Fido2NetworkConfig`: A sidecar (1:1) table for `WifiNetworkLocation` storing the `requires_fido2` flag uniquely.
- **views.py** - FIDO2 endpoints (`authenticate_start`, `authenticate_finish`) and `.well-known/assetlinks.json` pure brute serving (no Django templates used). Debug/logging is reduced for clean asynchronous logic understanding.
- **admin.py** - Django admin integration, injecting FIDO2 configuration as an inline element directly into the network edit form.
- **signals.py** - Django signal logic ensuring every explicitly created network gets a `Fido2NetworkConfig` automatically.
- **serializers.py** - API serializers for metadata payload injections.

### Data Flow

```
User registers passkey
  ↓
POST /fido2/register/start/ → Generate challenge
  ↓
POST /fido2/register/finish/ → Verify & store credential
  ↓
Credential stored in PasskeyCredential model

User authenticates later
  ↓
POST /fido2/authenticate/start/ → Generate challenge
  ↓
POST /fido2/authenticate/finish/ → Verify signature
  ↓
Auto-open 3-minute CSR signing window
  ↓
User can now request certificate
```

## Key Features

- **Isolated**: No changes to core mywifipass models or API
- **Extensible**: Add support for multiple Android apps via environment variables
- **Admin-integrated**: FIDO2 config appears as inline in network admin interface
- **Auto-validator**: Enabling FIDO2 automatically requires network admin approval
- **Database-backed**: Challenges stored in DB (not sessions), supports stateless deployments
- **Multi-app**: Official app always included, custom apps via `ANDROID_ADDITIONAL_APPS`

## Integration Points

### With mywifipass core

1. **WifiNetworkLocation** - One-to-one relationship via `Fido2NetworkConfig`
2. **WifiUser** - One-to-one relationship via `PasskeyCredential`
3. **Admin interface** - Inline admin integration without modifying core admin

### Backward Compatibility

If you remove `fido2_poc/`, the core app continues working unchanged. FIDO2 is entirely optional.

## Files Modified vs. Created

### New (always in fido2_poc/)
- `config.py`
- `android_dal.py`
- `serializers.py`
- `docs/` (this folder)

### Modified (in fido2_poc/)
- `signals.py` - Added validator auto-activation
- `admin.py` - Fixed checkbox appearance in new networks
- `views.py` - Uses config.py, dynamic assetlinks

### Unchanged (in mywifipass/)
- All core models and logic

### Modified core components (non-invasive)
- API `api/networks.py` and `api/users.py` - Dynamic metadata injection (`requires_fido2_validation` and endpoints URLs) via serializers like `WifiUserWifiPassSerializer`.
- `mywifipass/urls.py` - Explicit regex mapping for `.well-known/assetlinks.json` to prevent trailing slash redirects.

## No Static Files

The `.well-known/assetlinks.json` file is generated dynamically at `GET /.well-known/assetlinks.json`. There should be no static file.
