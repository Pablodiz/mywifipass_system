# Changelog

All notable changes to the MyWifiPass System.

---

## [1.3] - 2026-04/05 (Current)

> **Branch:** `48-feature-add-fido2-validator-poc` &nbsp;|&nbsp; **Status:** In Progress

### FIDO2 / WebAuthn - Passkey Validator

Passwordless biometric authorization replaces manual admin QR-code scanning for networks that require it.

- **New Django app:** `fido2_poc/` - sidecar app with minimal coupling to core
- **Four FIDO2 endpoints:** `/fido2/register/start/`, `/finish/`, `/authenticate/start/`, `/finish/`
- **Two authentication modes:**
  - *Discoverable mode* (default for Android) - empty `allowCredentials`, OS presents a passkey picker
  - *Email mode* (API-only) - validator provides the user's email to look up the specific passkey
- **New models:**
  - `PasskeyCredential` - stores WebAuthn credentials (1:1 with `WifiUser`)
  - `AuthenticationChallenge` - stateless challenge storage (database-backed, not session-based, for multi-worker Gunicorn)
  - `Fido2NetworkConfig` - per-network FIDO2 toggle (1:1 with `WifiNetworkLocation`, auto-created via signal)
- **Authorization flow:** successful passkey auth → 3-minute `allow_access_expiration` window → user can call `sign_certificate/`
- **Android Digital Asset Links** - served at `/.well-known/assetlinks.json` for cross-app credential sharing (official `app.mywifipass` always included)
- **Custom app support** - `ANDROID_ADDITIONAL_ORIGINS` and `ANDROID_ADDITIONAL_APPS` env vars for custom-compiled Android apps

### Wi-Fi Pass Metadata Enrichment

- Download payload now includes `fido2_authenticate_start_url`, `fido2_authenticate_finish_url`, `fido2_rp_id`, and `requires_fido2_validation`
- `is_user_authorized` is `false` when `requires_validator = True` on the network (Android app shows the authorization gate); `true` when no validator is required

### Admin Interface

- **FIDO2 Network Configs** admin section
- Inline FIDO2 configuration in the network edit form

---

## [1.2.1] - 2026-03

> **Branch:** `develop`

### N:M User-Network Relationship

- `WifiUser` ↔ `WifiNetworkLocation` changed from 1:N (ForeignKey `wifiLocation`) to **N:M** (ManyToManyField `networks`)
- Users can now access multiple networks simultaneously
- Data migration handles existing users (migrations 0009-0012)
- API endpoints and serializers updated for the new nested routing

### SSE Authorization Streaming

> **Branch:** `45-feature-automatic-retrieving-of-certificates` (merged into FIDO2 branch)

- `check_user_authorized` endpoint now supports **Server-Sent Events** via `Accept: text/event-stream` or `?stream=1`
- Real-time polling every 2 seconds for up to 3 minutes
- Events: `connected`, `heartbeat` (every ~10s), `authorized`, `timeout`
- Standard JSON mode preserved for non-streaming clients
- Backend test coverage for both modes

### Other Fixes & Cleanup

- Issue #44: `end_date` now includes the full final day (end-of-day time) - fixes premature access denial
- Removal of OpenWISP deployment files and references
- Environment configuration improvements (auto-populated `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`)
- `android_version` field deprecated on `WifiUser` (kept for DB compatibility)
- Email and CSR validation edge-case fixes

---

## [1.2] - 2026-02

> **Branch:** `security-hardening` &nbsp;|&nbsp; **Status:** Merged into `develop`

### Security Hardening (SEC-1 → SEC-9)

| Code | Description |
|---|---|
| SEC-1 | Removed overly permissive `ALLOWED_HOSTS` (`*`); replaced with environment-based configuration |
| SEC-2 | Enforced explicit `DJANGO_SECRET_KEY` configuration; auto-generated with `chmod 600` if missing |
| SEC-3 | Added CSRF protection in API and admin views (`CSRF_TRUSTED_ORIGINS` auto-populated) |
| SEC-4 | Full CSR validation: PEM format check, 10 KB size limit, self-signature verification, CN must match user name or email |
| SEC-5 | Made RADIUS certificate directory configurable via `RADIUS_CERT_DIR` env var; validated `secrets/.env` file permissions |
| SEC-6 | Rate limiting on all sensitive endpoints (5 throttles: login, CSR signing, authorization, download, validation) |
| SEC-7 | Email validation and sanitization: SMTP header injection prevention, RFC 5321 length check, duplicate email detection per network |
| SEC-8 | Removed debug information from production error responses (generic messages returned to clients) |
| SEC-9 | `LoginToken` auto-expiry and cleanup (opportunistic via `post_save` signal + periodic via `cleanup_expired_tokens` command) |

---

## [1.1] - 2025-09/10

> **Key architectural shift:** CSR-based certificate issuance replaces server-side generation.

### CSR Signing Architecture

- **New endpoint:** `POST /api/networks/{uuid}/users/{uuid}/sign_certificate/`
- Android app generates an RSA-2048 keypair using the standard JCE `KeyPairGenerator` and sends a Certificate Signing Request (CSR)
- Server validates the CSR, signs it with the network's CA, and returns the signed certificate + CA certificate
- **Private keys never touch the server** - fundamental security improvement over v1.0

### Symmetric Key Protection

- Each `WifiUser` gets a 32-byte random symmetric key (`certificates_symmetric_key`) via `secrets.token_bytes(32)`
- The key is delivered to the user in the Wi-Fi pass download JSON
- The CSR signing endpoint requires this key - serves as a shared secret between user and server

### Revocation & CRL

- Certificate revocation with automatic CRL updates via RADIUS file-system markers
- `CRL Distribution Points` extension embedded in all issued certificates
- Public CRL endpoint: `GET /api/networks/{uuid}/crl/`

### Wi-Fi Pass System

- One-time download enforcement (`has_downloaded_pass`)
- QR code generation with inline email embedding (Content-ID, not as attachment)
- Email delivery from background threads

### Legacy Code

- `WifiUser.create_certificate()` **deprecated** (commented out in `models.py`); replaced by `WifiUser.sign_csr()`

---

## [1.0] - 2025-07 (TFG - Degree Thesis)

> **Tag:** `v1.0` &nbsp;|&nbsp; Original thesis submission version.

### Core System

- **Django** web application with **PostgreSQL** backend
- **Server-side certificate generation** - certificates and private keys created entirely on the Django server
- **FreeRADIUS integration** via file-system sync (shared Docker volumes + cron scripts)
- **Docker Compose** deployment: `mywifipass` (Django), `radius` (FreeRADIUS), `database` (PostgreSQL 15)
- **OpenWISP integration** (removed in v1.2)

### User & Network Management

- `WifiUser` model: name, email, ID document, 1:1 relationship with a single network
- `WifiNetworkLocation` model: SSID, location metadata, CA association
- Django Admin panel with email/QR actions
- `LoginToken` (UUID, 5-min expiry) for admin app QR login

### PKI Library

- Fork of **OpenWISP django-x509** (BSD 3-Clause) as `django_x509/`
- Abstract CA and Cert models with swappable concrete implementations
- Defaults: 2048-bit RSA, SHA-256 digest, 365-day cert validity

> **Note:** In v1.0 the server generated both the certificate AND the private key, storing the private key in the database. This was replaced in v1.1 by the CSR architecture where private keys are generated on-device and never transmitted.

---

## Migration Notes

### From 1.2.1 to 1.3

1. New FIDO2 models require migrations: `python manage.py migrate`
2. New env vars: `ANDROID_ADDITIONAL_ORIGINS`, `ANDROID_ADDITIONAL_APPS`
3. `android_version` field on `WifiUser` is deprecated and no longer tracked

### From 1.2 to 1.2.1

1. **Breaking:** `user.wifiLocation` (ForeignKey) replaced by `user.networks` (ManyToManyField)
2. Code that accesses `user.wifiLocation` must be updated to `user.networks.first()` or iterate `user.networks.all()`
3. SSE support is opt-in via `Accept` header or `?stream=1` - standard JSON clients are unaffected

### From 1.1 to 1.2

1. `DJANGO_SECRET_KEY` is now required (auto-generated on first Docker start if missing)
2. `ALLOWED_HOSTS` must be explicitly configured - wildcard `*` no longer permitted
3. `RADIUS_CERT_DIR` env var added (optional, has default)
4. Rate limiting is now active by default
5. Set up a cron job for `manage.py cleanup_expired_tokens`

### From 1.0 to 1.1

1. **Breaking:** Old `create_certificate()` removed. Clients must use CSR flow via `POST /sign_certificate/`
2. **Breaking:** Certificates no longer generated server-side with private keys in DB. Existing v1.0 certificates should be revoked and re-issued via CSR
3. `certificates_symmetric_key` field added - existing users need this set before using the CSR endpoint
4. CRL infrastructure added - FreeRADIUS config must reference CRL distribution point URLs
