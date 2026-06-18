# API Reference

The REST API follows nested RESTful conventions. Interactive documentation is available at:

- **Swagger UI:** `http://<DOMAIN>/api/swagger`
- **ReDoc:** `http://<DOMAIN>/api/redoc`
- **OpenAPI JSON:** `http://<DOMAIN>/api/swagger.json`

---

## Authentication

All endpoints except public ones require authentication.

### Method 1: Password Authentication

```http
POST /api/login/password
Content-Type: application/json

{
  "username": "admin",
  "password": "your_password"
}
```

**Response:**
```json
{
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
}
```

### Method 2: QR Token Authentication (Admin App)

```http
POST /api/login/token
Content-Type: application/json

{
  "username": "admin",
  "token": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response:** Same as password auth - a DRF auth token.

The QR token is obtained by scanning the Admin QR code displayed at `/admin/qr/`. Tokens expire after 5 minutes.

### Using the Auth Token

Include in all authenticated requests:

```
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
```

### Public Endpoints

The following endpoints do **not** require authentication:
- `GET /api/swagger`, `/api/redoc`, `/api/swagger.json`
- `GET /api/networks/{uuid}/crl/`
- `GET /api/networks/{uuid}/users/{uuid}/download/`
- `GET /api/networks/{uuid}/users/{uuid}/qr/`
- `POST /api/networks/{uuid}/users/{uuid}/sign_certificate/`
- `GET /api/networks/{uuid}/users/{uuid}/check_user_authorized/`
- `POST /api/networks/{uuid}/users/{uuid}/downloaded/`

---

## Networks API

**Base URL:** `/api/networks/`

| Method | URL | Auth | Description |
|---|---|---|---|
| `GET` | `/api/networks/` | Admin | List all networks |
| `POST` | `/api/networks/` | Admin | Create a new network |
| `GET` | `/api/networks/{network_uuid}/` | Admin | Get network details |
| `PUT` | `/api/networks/{network_uuid}/` | Admin | Full update |
| `PATCH` | `/api/networks/{network_uuid}/` | Admin | Partial update |
| `DELETE` | `/api/networks/{network_uuid}/` | Admin | Delete network |
| `GET` | `/api/networks/{network_uuid}/crl/` | Public | Get Certificate Revocation List |

### Create a Network

```http
POST /api/networks/
Authorization: Token abc123...
Content-Type: application/json

{
  "name": "TechConf 2026",
  "SSID": "TechConf2026",
  "location": "Main Auditorium",
  "description": "Wi-Fi access for conference attendees",
  "brief_description": "Conference Wi-Fi",
  "start_date": "2026-06-01",
  "end_date": "2026-06-03",
  "is_registration_open": true,
  "is_visible_in_web": true,
  "is_enabled_in_radius": true,
  "requires_validator": true,
  "send_emails_automatically": true
}
```

**Response:** `201 Created` with the full network object including `location_uuid`.

**Side effects on creation:**
- A Certificate Authority (CA) is created
- A RADIUS server certificate is generated
- Certificates are exported to the shared RADIUS volume

### List Networks

```http
GET /api/networks/
Authorization: Token abc123...
```

**Response:**
```json
[
  {
    "location_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "name": "TechConf 2026"
  }
]
```

### Get Network Details

```http
GET /api/networks/550e8400-e29b-41d4-a716-446655440000/
Authorization: Token abc123...
```

**Response:** Full network object with all fields.

### Get CRL (Public)

```http
GET /api/networks/550e8400-e29b-41d4-a716-446655440000/crl/
```

**Response:** `200 OK` with PEM-encoded CRL as `text/plain`. This is consumed directly by FreeRADIUS.

### Update a Network

Updating `name`, `start_date`, or `end_date` triggers CA regeneration and certificate re-export.

Changing `is_enabled_in_radius`:
- From `true` to `false`: marks the SSID for deletion
- From `false` to `true`: exports certificates again

---

## Users API

**Base URL:** `/api/networks/{network_uuid}/users/`

| Method | URL | Auth | Description |
|---|---|---|---|
| `GET` | `.../users/` | Admin | List users in the network |
| `POST` | `.../users/` | Admin | Create a new user |
| `GET` | `.../users/{user_uuid}/` | Admin | Get user details |
| `PUT` | `.../users/{user_uuid}/` | Admin | Full update |
| `PATCH` | `.../users/{user_uuid}/` | Admin | Partial update |
| `DELETE` | `.../users/{user_uuid}/` | Admin | Delete user |
| `GET` | `.../users/{user_uuid}/validate/` | Admin | Validate user for event attendance |
| `POST` | `.../users/{user_uuid}/authorize/` | Admin | Authorize user (opens CSR signing window) |
| `GET` | `.../users/{user_uuid}/download/` | Public | Download Wi-Fi pass (one-time) |
| `GET` | `.../users/{user_uuid}/qr/` | Public | QR code image for the Wi-Fi pass |
| `POST` | `.../users/{user_uuid}/sign_certificate/` | Public* | Sign user's CSR and return certificates |
| `GET` | `.../users/{user_uuid}/check_user_authorized/` | Public | Poll authorization status (supports SSE) |
| `POST` | `.../users/{user_uuid}/downloaded/` | Public | Mark pass as downloaded |

> *`sign_certificate/` is technically public but requires the user's 32-byte symmetric key as a token, which acts as a shared secret.

### Create a User

```http
POST /api/networks/{network_uuid}/users/
Authorization: Token abc123...
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john@example.com",
  "id_document": "12345678A"
}
```

**Response:** `201 Created` with user UUID and details.

### Get User Details

```http
GET /api/networks/{network_uuid}/users/{user_uuid}/
Authorization: Token abc123...
```

**Response fields:**
```json
{
  "user_uuid": "...",
  "name": "John Doe",
  "email": "john@example.com",
  "id_document": "12345678A",
  "has_attended": false,
  "has_downloaded_pass": false,
  "allow_access_expiration": null,
  "network_common_name": "TechConf_2026",
  "ssid": "TechConf2026",
  "location": "Main Auditorium",
  "start_date": "2026-06-01",
  "end_date": "2026-06-03",
  "description": "Wi-Fi access for conference attendees",
  "location_name": "TechConf 2026",
  "location_uuid": "...",
  "certificates_symmetric_key": "a1b2c3...",
  "is_user_authorized": false,
  "requires_fido2_validation": true
}
```

### Sign a Certificate (CSR)

This is the critical endpoint used by the Android app to obtain EAP-TLS client certificates.

```http
POST /api/networks/{network_uuid}/users/{user_uuid}/sign_certificate/
Content-Type: application/json

{
  "csr": "-----BEGIN CERTIFICATE REQUEST-----\nMIIC...\n-----END CERTIFICATE REQUEST-----",
  "token": "hex_encoded_32_byte_symmetric_key"
}
```

**Validation performed:**
1. `token` (hex-encoded) must match the user's `certificates_symmetric_key` (32 bytes)
2. CSR must be valid PEM format with correct headers
3. CSR size must be under 10 KB (DoS prevention)
4. CSR signature must verify against its own public key (prevents tampering)
5. CSR Common Name (CN) must match either the user's name or email
6. User must be assigned to the requested network

> **Note:** `allow_access_expiration` is **not** enforced server-side in this endpoint. The authorization window is enforced at the client level via the `check_user_authorized` SSE stream.

**Response (200):**
```json
{
  "signed_cert": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
  "ca_cert": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----"
}
```

**Side effects:**
- Previous certificate (if any) is revoked
- A new `MyCustomCert` record is created
- User is deauthorized (`allow_access_expiration = None`, `has_attended = True`)

### Download Wi-Fi Pass

```http
GET /api/networks/{network_uuid}/users/{user_uuid}/download/
```

**Response (200):**
```json
{
  "email": "john@example.com",
  "network_common_name": "TechConf_2026",
  "ssid": "TechConf2026",
  "location": "Main Auditorium",
  "start_date": "2026-06-01",
  "end_date": "2026-06-03",
  "description": "Wi-Fi access for conference attendees",
  "location_name": "TechConf 2026",
  "certificates_symmetric_key": "a1b2c3...",
  "requires_fido2_validation": true,
  "fido2_authenticate_start_url": "http://wifi.example.com/fido2/authenticate/start/",
  "fido2_authenticate_finish_url": "http://wifi.example.com/fido2/authenticate/finish/",
  "fido2_rp_id": "wifi.example.com",
  "validation_url": "http://wifi.example.com/api/networks/.../users/.../validate/",
  "certificates_url": "http://wifi.example.com/api/networks/.../users/.../sign_certificate/",
  "has_downloaded_url": "http://wifi.example.com/api/networks/.../users/.../downloaded/",
  "check_user_authorized_url": "http://wifi.example.com/api/networks/.../users/.../check_user_authorized/",
  "is_user_authorized": false
}
```

- **One-time use:** After download, `has_downloaded_pass` is set server-side via the `downloaded/` endpoint
- **`is_user_authorized`** is `false` when `requires_validator = True` (Android app must go through the validation gate), and `true` when `requires_validator = False` (user is immediately authorized, no gate needed).

### QR Code

```http
GET /api/networks/{network_uuid}/users/{user_uuid}/qr/
```

**Response:** PNG image with `Content-Type: image/png`.

The QR encodes the user's download URL through a redirect landing page.

### Validate User

```http
GET /api/networks/{network_uuid}/users/{user_uuid}/validate/
Authorization: Token abc123...
```

**Response (200):**
```json
{
  "id_document": "12345678A",
  "name": "John Doe",
  "authorize_url": "http://wifi.example.com/api/networks/.../users/.../authorize/"
}
```

**Response (403)** if user has already attended:
```json
{
  "error": "User has already accessed the event."
}
```

### Authorize User

```http
POST /api/networks/{network_uuid}/users/{user_uuid}/authorize/
Authorization: Token abc123...
```

**Response (200):**
```json
{
  "message": "The user can now join the network."
}
```

Sets `has_attended = True` and `allow_access_expiration = now + 3 minutes`. During this window, the user can call `sign_certificate/`.

**Response (403)** if user's certificate is already revoked.

### Check User Authorized

This endpoint supports both standard JSON and **Server-Sent Events (SSE)** streaming.

#### Standard Mode

```http
GET /api/networks/{network_uuid}/users/{user_uuid}/check_user_authorized/
```

**Response (200)** if authorized:
```json
{
  "message": "User is authorized to access the network."
}
```

**Response (403)** if not authorized:
```json
{
  "error": "User is not allowed to access"
}
```

#### SSE Streaming Mode

To use SSE streaming, either:
- Set `Accept: text/event-stream` header
- Or add `?stream=1` query parameter

```bash
curl -N -H "Accept: text/event-stream" \
  http://wifi.example.com/api/networks/{uuid}/users/{uuid}/check_user_authorized/
```

**SSE Events:**

```
event: connected
data: {"user_uuid":"...","network_uuid":"...","timestamp":"..."}

event: heartbeat
data: {"timestamp":"..."}

event: authorized
data: {"user_uuid":"...","network_uuid":"...","authorized_at":"...","expires_at":"..."}

event: timeout
data: {"message":"Authorization was not granted within stream window."}
```

The stream polls every 2 seconds for up to 90 checks (3 minutes total), sending heartbeats every ~10 seconds. It closes when the user is authorized or the timeout is reached.

### Mark as Downloaded

```http
POST /api/networks/{network_uuid}/users/{user_uuid}/downloaded/
```

**Response (200):**
```json
{
  "message": "The user has downloaded the pass."
}
```

Sets `has_downloaded_pass = True`, preventing further downloads.

---

## FIDO2 / WebAuthn API

**Base URL:** `/fido2/`

| Method | URL | Type | Description |
|---|---|---|---|
| `GET` | `/fido2/register/` | HTML | Registration page |
| `POST` | `/fido2/register/start/` | JSON | Begin registration challenge |
| `POST` | `/fido2/register/finish/` | JSON | Complete registration |
| `GET` | `/fido2/authenticate/` | HTML | Authentication page |
| `POST` | `/fido2/authenticate/start/` | JSON | Begin authentication challenge |
| `POST` | `/fido2/authenticate/finish/` | JSON | Complete authentication |

See [FIDO2 Guide](fido2-guide.md) for detailed request/response schemas and flows.

---

## Helper Functions (`api/urls.py`)

The module exports reusable functions for building API URLs programmatically:

```python
from mywifipass.api.urls import (
    base_url, wifipass_download_url, user_qr_url,
    sign_certificate_url, crl_url, authorize_url,
    check_user_authorized_url, validation_url, email_url,
    certificates_symmetric_key_url, certificates_url,
    has_downloaded_url,
)
```

| Function | Parameters | Returns |
|---|---|---|
| `base_url(user, network=None)` | `WifiUser`, `WifiNetworkLocation` | User's base URL in a network |
| `wifipass_download_url(user, network=None)` | `WifiUser`, `WifiNetworkLocation` | Download URL |
| `user_qr_url(user, network=None)` | `WifiUser`, `WifiNetworkLocation` | QR code image URL |
| `sign_certificate_url(user, network=None)` | `WifiUser`, `WifiNetworkLocation` | CSR signing URL |
| `crl_url(network)` | `WifiNetworkLocation` | CRL URL |
| `authorize_url(user, network=None)` | `WifiUser`, `WifiNetworkLocation` | Authorization URL |
| `check_user_authorized_url(user, network=None)` | `WifiUser`, `WifiNetworkLocation` | SSE-compatible authorization check URL |
| `validation_url(user, network=None)` | `WifiUser`, `WifiNetworkLocation` | Validation URL |
| `email_url(user, network=None)` | `WifiUser`, `WifiNetworkLocation` | Email redirect URL (GitHub Pages) |
| `certificates_symmetric_key_url(user, network=None)` | `WifiUser`, `WifiNetworkLocation` | Symmetric key URL |
| `certificates_url(user, network=None)` | `WifiUser`, `WifiNetworkLocation` | Certificates URL |
| `has_downloaded_url(user, network=None)` | `WifiUser`, `WifiNetworkLocation` | Mark-as-downloaded URL |

---

## Rate Limiting

| Scope | Limit | Type | Affected Endpoints |
|---|---|---|---|
| `login_attempt` | 5/minute | Per IP | `/api/login/*` |
| `certificate_signing` | 3/minute | Per user | `sign_certificate/` |
| `authorization` | 10/minute | Per user | `authorize/` |
| `download` | 20/minute | Per IP | `download/`, `qr/`, `downloaded/` |
| `validation` | 10/minute | Per IP | `validate/`, `check_user_authorized/` |

When a rate limit is exceeded, the API returns `429 Too Many Requests`.

---

## Error Response Format

All errors follow a consistent format:

```json
{
  "error": "Human-readable error description"
}
```

Common HTTP status codes:
- `400` - Bad request (validation error, invalid CSR, etc.)
- `401` - Unauthorized (missing or invalid auth token)
- `403` - Forbidden (user already attended, certificate revoked, invalid symmetric key)
- `404` - Not found
- `429` - Rate limit exceeded
- `500` - Internal server error
