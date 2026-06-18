# FIDO2 / Passkey Integration Guide

MyWifiPass System implements **FIDO2/WebAuthn** (commonly known as "passkeys") as an optional authorization mechanism for Wi-Fi networks. This guide covers the technical details of the implementation.

---

## Concept

When a network has `requires_fido2 = True`, users cannot obtain their EAP-TLS certificates directly. Instead, a **passkey authentication** must happen first. On successful authentication, the user receives a **3-minute window** during which they can sign a CSR and obtain their Wi-Fi certificate.

Two UI surfaces are supported, both using discoverable mode:

- **Browser flow:** A user opens `/fido2/authenticate/` in their browser. The browser presents all passkeys registered for this domain. The user selects their passkey and provides biometric/PIN. Their own 3-minute CSR window is opened.
- **Android app (Credential Manager):** The Android app calls `/fido2/authenticate/start/` with an empty body. Android Credential Manager presents available passkeys. The user authenticates; their own 3-minute CSR window is opened.

Email mode is also available via API: the user provides their own email in the `start` request, and their specific passkey is requested by credential ID. It is not exposed in the browser UI.

In all cases the authorization is time-limited (3 minutes) and cryptographically verified.

---

## Architecture

The FIDO2 implementation is a **sidecar Django app** (`fido2_poc/`) with minimal coupling to the core system:

```
fido2_poc/
├── __init__.py
├── admin.py
├── android_dal.py       # Android Digital Asset Links generator
├── apps.py
├── config.py            # RP ID, RP name, origins from env vars
├── models.py            # PasskeyCredential, AuthenticationChallenge, Fido2NetworkConfig
├── serializers.py
├── signals.py
├── templates/           # HTML pages for registration and authentication
├── urls.py
└── views.py             # register_page, register_start, register_finish, authenticate_page, authenticate_start, authenticate_finish, assetlinks_json
```

### Models

#### `PasskeyCredential`
Stores WebAuthn credentials. One-to-one with `WifiUser`.

| Field | Type | Description |
|---|---|---|
| `wifi_user` | 1:1 FK | Reference to the Wi-Fi user |
| `credential_id` | Char(500), unique | Base64-encoded FIDO2 credential ID |
| `public_key` | Text | JSON-serialized JWK for signature verification |
| `sign_count` | Integer | Signature counter for replay detection |
| `attestation_format` | Char(50) | e.g., `none`, `packed`, `fido-u2f` |
| `algorithm` | Integer | COSE algorithm (ES256 = -7) |
| `created_at` | DateTime | When the passkey was registered |
| `is_active` | Boolean | Whether the credential can be used |
| `last_used` | DateTime | Last successful authentication |

#### `AuthenticationChallenge`
Stateless challenge storage (not session-based, for mobile client compatibility).

| Field | Type | Description |
|---|---|---|
| `email` | Email, nullable | For email-based authentication flow |
| `session_id` | UUID, nullable | For discoverable (session-based) flow |
| `challenge` | Text | Base64-encoded WebAuthn challenge |
| `created_at` | DateTime | Creation timestamp |

Supports two modes:

1. **Email mode:** `email` is set, `session_id` is null. Challenge is looked up by email.
2. **Discoverable mode (default for Android):** `email` is null, `session_id` is a UUID. Challenge is looked up by `session_id`. The browser presents all available passkeys for the domain.

Stale challenges (>5 minutes) are purged at the start of each new request.

#### `Fido2NetworkConfig`
One-to-one with `WifiNetworkLocation`. Determines whether a network requires FIDO2.

| Field | Type | Description |
|---|---|---|
| `network` | 1:1 FK | The network |
| `requires_fido2` | Boolean | Enables FIDO2 validation |

---

## Registration Flow

### 1. Start Registration

```http
POST /fido2/register/start/
Content-Type: application/json

{
  "email": "validator@example.com"
}
```

The server:
1. Creates (or retrieves) a `WifiUser` with the given email
2. Checks that the user doesn't already have an active passkey
3. Generates WebAuthn registration options with:
   - `resident_key = REQUIRED` (discoverable credential)
   - `user_verification = REQUIRED`
   - `attestation = NONE`
4. Stores the challenge in the session

**Response:**
```json
{
  "challenge": "base64url_challenge",
  "rp": {"name": "MyWifiPass", "id": "wifi.example.com"},
  "user": {
    "id": "base64url_user_uuid",
    "name": "validator.example.com",
    "displayName": "validator.example.com"
  },
  "pubKeyCredParams": [
    {"type": "public-key", "alg": -7},
    {"type": "public-key", "alg": -257}
  ],
  "timeout": 60000,
  "attestation": "none",
  "authenticatorSelection": {
    "authenticatorAttachment": null,
    "residentKey": "required",
    "userVerification": "required"
  }
}
```

### 2. Complete Registration

```http
POST /fido2/register/finish/
Content-Type: application/json

{
  "email": "validator@example.com",
  "credential": {
    "id": "base64url_credential_id",
    "rawId": "base64url_raw_id",
    "response": {
      "clientDataJSON": "base64url_client_data",
      "attestationObject": "base64url_attestation"
    },
    "type": "public-key"
  }
}
```

The server:
1. Verifies the attestation response against the stored challenge
2. Validates the origin against `EXPECTED_ORIGINS`
3. Creates/updates a `PasskeyCredential` record linked to the `WifiUser`

**Response:**
```json
{
  "success": true,
  "message": "Passkey registered successfully"
}
```

---

## Authentication Flow

### Two Modes

#### Email Mode (API-Only)

The user provides their own email. The server looks up their registered passkey and returns its credential ID in `allowCredentials`. Not available in the browser UI (which uses discoverable mode only).

```http
POST /fido2/authenticate/start/
Content-Type: application/json

{
  "email": "wifi_user@example.com"
}
```

**Response:**
```json
{
  "challenge": "base64url_challenge",
  "rpId": "wifi.example.com",
  "allowCredentials": [
    {
      "id": "base64url_credential_id",
      "type": "public-key"
    }
  ],
  "timeout": 60000,
  "userVerification": "preferred"
}
```

Note: `session_id` is **not** included in email mode. `userVerification` is set to `"preferred"` for Android Credential Manager compatibility. The `allowCredentials` list tells the browser exactly which passkey to request.

#### Discoverable Mode (Default for Android App)

No email needed. The browser/Android Credential Manager presents all available passkeys.

```http
POST /fido2/authenticate/start/
Content-Type: application/json

{}
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "challenge": "base64url_challenge",
  "rpId": "wifi.example.com",
  "allowCredentials": [],
  "timeout": 60000,
  "userVerification": "preferred"
}
```

Empty `allowCredentials` = discoverable mode. The user picks a passkey from the OS-level picker.

### Complete Authentication

```http
POST /fido2/authenticate/finish/
Content-Type: application/json

{
  "email": "wifi_user@example.com",  // Only for email mode
  "session_id": "550e8400-...",      // Only for discoverable mode
  "credential": {
    "id": "base64url_credential_id",
    "rawId": "base64url_raw_id",
    "response": {
      "clientDataJSON": "base64url_client_data",
      "authenticatorData": "base64url_auth_data",
      "signature": "base64url_signature"
    },
    "type": "public-key"
  }
}
```

The server:
1. Retrieves the challenge by email OR session_id
2. Finds the `PasskeyCredential`: in discoverable mode by `credential.id`; in email mode by looking up the user's single active passkey via their email
3. Verifies the assertion signature using the stored public key
4. Validates the origin and RP ID
5. Updates `sign_count` and `last_used`
6. Sets `allow_access_expiration = now + 3 minutes` on the Wi-Fi user
7. Deletes the used challenge (replay prevention)

**Response:**
```json
{
  "success": true,
  "message": "CSR signing window opened (3 minutes)",
  "expires_at": "2026-06-11T14:35:42.123456+00:00"
}
```

---

## Relying Party Configuration

The Relying Party (RP) is configured in `fido2_poc/config.py` from environment variables:

```python
RP_ID = DOMAIN.split(':')[0]  # e.g., wifi.example.com
RP_NAME = 'MyWifiPass'
ORIGIN = f'https://{DOMAIN}' if SSL else f'http://{DOMAIN}'
EXPECTED_ORIGINS = [
    f'https://{DOMAIN}',
    f'http://{DOMAIN}',
    'android:apk-key-hash:...',  # Official app (release key)
    'android:apk-key-hash:...',  # Official app (debug key)
]
```

### Adding Custom Android Apps

To add origins for custom-compiled Android apps:

```ini
# .env
ANDROID_ADDITIONAL_ORIGINS=android:apk-key-hash:CUSTOM_HASH1,android:apk-key-hash:CUSTOM_HASH2
```

To add custom apps to Digital Asset Links:

```ini
# .env
ANDROID_ADDITIONAL_APPS=[{"package_name":"com.mycompany.mywifipass","sha256":"AA:BB:CC:DD:..."}]
```

---

## Digital Asset Links

The endpoint `/.well-known/assetlinks.json` serves Android Digital Asset Links, enabling the Android app to share FIDO2 credentials with the browser. Generated dynamically by `fido2_poc/android_dal.py`.

The official `app.mywifipass` package is always included. Custom apps can be added via `ANDROID_ADDITIONAL_APPS`.

---

## Security Considerations

1. **Challenge storage:** Authentication challenges are stored in the database (not HTTP session) to support multi-worker Gunicorn deployments and stateless mobile clients. Registration challenges are stored in the HTTP session (only browser-based, single-worker compatible).
2. **Replay detection:** `sign_count` is incremented on each successful authentication and verified against the stored value.
3. **Origin validation:** The WebAuthn library validates the origin against `EXPECTED_ORIGINS` to prevent phishing.
4. **User Verification:** Registration sets `"userVerification": "required"` in the client JSON; authentication sets `"userVerification": "preferred"` for Android Credential Manager compatibility. The server-side `webauthn` library is still initialised with `REQUIRED` in both cases.
5. **Time-limited authorization:** The 3-minute CSR window prevents indefinite access.
6. **Stale challenge cleanup:** Challenges older than 5 minutes are purged at the start of each new request.

---

## Enabling FIDO2 on a Network

1. Go to Django Admin → **FIDO2 Network Configs**
2. Click **Add**
3. Select the network
4. Check **Requires FIDO2**
5. Save

This sets `requires_validator = True` on the network as a side effect. Disabling FIDO2 does not clear `requires_validator` - admins may have other reasons to require validation.

---

## Testing FIDO2

See the [Development Guide](development.md) for testing instructions, including the `test_pages.py` smoke test.

```bash
# Quick test that FIDO2 pages are accessible
curl -I http://localhost:10000/fido2/register/
curl -I http://localhost:10000/fido2/authenticate/
```
