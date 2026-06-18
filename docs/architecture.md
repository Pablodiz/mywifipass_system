# System Architecture

## Component Overview

The system is deployed as three Docker services communicating over an internal network (`172.19.0.0/16`):

```mermaid
graph TD
    INET["INTERNET / LOCAL NETWORK"]
    CLIENT["Wi-Fi Client\n(Android App / OS)"]
    AP["Access Point"]

    INET --> CLIENT
    CLIENT -->|"EAP-TLS 802.1X"| AP
    AP -->|"RADIUS UDP 1812"| MYWP

    subgraph DC["DOCKER COMPOSE"]
        MYWP["mywifipass\nDjango + Gunicorn\n• Admin Web UI\n• REST API\n• PKI Engine\n• FIDO2 WebAuthn\n• QR / Email"]
        RADIUS_SVC["radius\nFreeRADIUS\n• EAP-TLS handler\n• CRL validation\n• SSID automation"]
        DB_SVC[("database\nPostgreSQL\n• Users / Networks / Certs")]
        VOLS["Shared Volumes\n• server_certs/\n• logos/\n• secrets/"]

        MYWP -->|writes certs| VOLS
        VOLS -->|certs exported| RADIUS_SVC
        MYWP --- DB_SVC
    end
```

### Service Details

| Service | Image / Build | Port | Role |
|---|---|---|---|
| `mywifipass` | `python:3.13-slim-bullseye` (custom Dockerfile) | `${WEBAPP_PORT}:8000` | Django web app + REST API + PKI engine |
| `radius` | `freeradius/freeradius-server:latest` (custom Dockerfile) | `${RADIUS_PORT}:1812/udp` | EAP-TLS authentication server |
| `database` | `postgres:15` | Internal only | Data persistence |

The `mywifipass` container depends on `database` being healthy (verified via `pg_isready`).

---

## EAP-TLS Authentication Flow

```mermaid
sequenceDiagram
    participant User
    participant App as Android App
    participant API as API Server
    participant PKI as Django PKI
    participant RADIUS as FreeRADIUS
    participant AP as Access Point

    User->>App: 1. Receives email/QR
    User->>App: 2. Opens app
    App->>API: 3. GET /download/ (scan QR)
    API-->>App: symmetric key + metadata

    App->>API: 4. POST /sign_certificate/ (CSR + key)
    API->>PKI: 5. Validate CSR, sign
    PKI-->>API: signed certificate
    API-->>App: cert + CA cert

    App->>App: 6. Configure Wi-Fi profile
    App->>AP: 7. Connect to Wi-Fi (EAP-TLS)
    AP->>RADIUS: EAP-TLS handshake
    RADIUS-->>AP: Accept / Reject
    AP-->>User: Connected
```

### Key Steps

1. **Wi-Fi Pass Delivery** - User receives an email with a unique download URL and QR code. The URL encodes the user's UUID. The 32-byte symmetric key is returned by the download endpoint, not embedded in the URL.

2. **Wi-Fi Pass Download** - The Android app scans the QR from the user's email, which encodes a redirect URL to `GET /api/networks/{uuid}/users/{uuid}/download/`. The response includes the network metadata and the user's 32-byte symmetric key (`certificates_symmetric_key`), which acts as a shared secret to authenticate the CSR signing request.

3. **CSR Signing** - The app generates an RSA-2048 keypair using the standard JCE `KeyPairGenerator` and sends a Certificate Signing Request (CSR) to `POST /sign_certificate/`. The server validates:
   - The symmetric key (passed as the request token) matches the user's stored key
   - The CSR is in valid PEM format and properly self-signed
   - The Common Name (CN) in the CSR matches the user's name or email
   - The user is assigned to the requested network

   If `requires_validator = True`, the app uses the `check_user_authorized` SSE stream to wait for the authorization window to open before calling this endpoint. The authorization window is not enforced server-side in `sign_certificate` itself.

4. **EAP-TLS Handshake** - The Android device presents its client certificate to the access point, which forwards it to FreeRADIUS. FreeRADIUS verifies the certificate chain against the CA and checks the CRL.

---

## FIDO2 Authorization Flow (Optional Per-Network)

When `requires_validator = True` on a network, users need a **3-minute authorization window** before they can sign a CSR. This window is opened by the user authenticating with their own registered passkey:

```mermaid
sequenceDiagram
    participant User as Wi-Fi User
    participant App as Browser / App
    participant FIDO2 as /fido2/
    participant Django

    User->>App: 1. Opens auth page (browser) or taps in Android
    App->>FIDO2: 2. POST /authenticate/start/ (empty body, discoverable)
    FIDO2-->>App: 3. challenge + session_id
    User->>App: 4. Selects passkey (biometric/PIN)
    App->>FIDO2: 5. POST /authenticate/finish/ (session_id + credential)
    FIDO2->>Django: 6. Verify signature
    Django-->>FIDO2: 7. Sets allow_access_expiration = now + 3 min
    FIDO2-->>App: 8. 200 OK (window open)
    Note over App: Android app: navigate to NetworkDetailScreen, then start SSE
    App->>Django: 9. GET /check_user_authorized/ (SSE stream)
    Django-->>App: 10. "authorized" event
    App->>Django: 11. POST /sign_certificate/ (CSR)
    Django-->>App: 12. signed certificate
```

### Two FIDO2 Modes

1. **Discoverable Mode (default)** - No email needed. The browser/Android Credential Manager presents all available passkeys for the domain. The user picks their passkey and authenticates. The credential ID maps directly to the stored `PasskeyCredential`, opening that user's CSR window.

2. **Email Mode (API-only)** - The user provides their own email in the `start` request. The server looks up their associated passkey and creates the challenge keyed by email. Not exposed in the browser UI.

---

## RADIUS File-System Integration

Django does not communicate with FreeRADIUS over the network for configuration. Instead, they share a **Docker volume** (`shared-certs`). A background `watch_ssids.sh` process (inotify) in the RADIUS container detects new files and immediately triggers `process_ssids.sh`. A periodic cron job handles automatic CRL refresh.

```
shared-certs/:
├── pending/       # Django writes new SSID certs here → process_ssids.sh adds them
├── processed/     # SSIDs already active in FreeRADIUS (moved from pending/)
├── deletion/      # Markers for SSIDs to remove → remove_ssids.sh deletes them
├── update_crl/    # Markers for CRL regeneration → update_crl.sh refreshes
└── logs/          # Per-SSID log files from shell scripts
```

| Directory | Writer | Reader | Action |
|---|---|---|---|
| `pending/` | Django (on network save) | `watch_ssids.sh` → `process_ssids.sh` | Creates RADIUS virtual server config, copies certs |
| `deletion/` | Django (on network delete/disable) | `watch_ssids.sh` → `process_ssids.sh` | Removes virtual server config and certs |
| `update_crl/` | Django (on certificate revocation) | `watch_ssids.sh` → `process_ssids.sh` | Regenerates Certificate Revocation Lists |

When `process_ssids.sh` makes changes it sends `pkill` to FreeRADIUS, restarting it to pick up the new configuration. `automatic_crl_update.sh` runs every 12 hours via cron as a safety net for all active SSIDs.

---

## Database Schema (Simplified)

```mermaid
erDiagram
    MyCustomCA {
        int id PK
        string name
        string common_name
        text certificate
        text private_key
        date validity_start
        date validity_end
        int serial_number
        int key_length
        string digest
        json extensions
    }
    MyCustomCert {
        int id PK
        int ca FK
        string name
        string common_name
        string email
        string serial_number
        text certificate
        text private_key
        date validity_start
        date validity_end
        bool revoked
        datetime revoked_at
    }
    WifiNetworkLocation {
        uuid location_uuid PK
        string name
        string SSID
        string location
        string description
        date start_date
        date end_date
        uuid certificates_CA FK
        int radius_Certificate FK
        bool is_registration_open
        bool is_visible_in_web
        bool is_enabled_in_radius
        bool requires_validator
        bool send_emails_automatically
    }
    WifiUser {
        uuid user_uuid PK
        string name
        string email
        string id_document
        binary certificates_symmetric_key
        int certificate FK
        bool has_attended
        bool has_downloaded_pass
        datetime allow_access_expiration
        bool email_sent
        datetime email_sent_date
    }
    PasskeyCredential {
        int id PK
        uuid wifi_user FK
        string credential_id
        text public_key
        int sign_count
        int algorithm
        string attestation_format
        datetime created_at
        bool is_active
        datetime last_used
    }
    AuthenticationChallenge {
        int id PK
        string email
        uuid session_id
        text challenge
        datetime created_at
    }
    Fido2NetworkConfig {
        int id PK
        uuid network FK
        bool requires_fido2
    }
    LoginToken {
        int id PK
        int user FK
        uuid token
        datetime created_at
        datetime expires_at
    }

    MyCustomCA ||--o{ MyCustomCert : "signs"
    WifiNetworkLocation }o--|| MyCustomCA : "certificates_CA"
    WifiNetworkLocation }o--o| MyCustomCert : "radius_Certificate"
    WifiNetworkLocation }o--o{ WifiUser : "M2M networks"
    WifiUser }o--o| MyCustomCert : "certificate"
    WifiUser ||--o| PasskeyCredential : "passkey"
    WifiNetworkLocation ||--o| Fido2NetworkConfig : "fido2_config"
```

---

## Data Flow Summary

1. **Admin creates a network** → Django generates a CA certificate, exports server certificates to `shared-certs/pending/` → `watch_ssids.sh` (inotify) detects the new files and triggers `process_ssids.sh`, which creates the virtual server and enables EAP-TLS for that SSID.

2. **Admin creates/imports users** → Django assigns them to networks. If `send_emails_automatically = True`, the system sends an email with a Wi-Fi pass (download URL + QR code). The 32-byte symmetric key is returned by the `/download/` endpoint when the user first opens the URL, not embedded in the email.

3. **User opens the Android app** → Scans the QR from their email (encodes the download URL) → Downloads Wi-Fi pass data including symmetric key → Optionally performs FIDO2 if required → Generates a keypair and CSR → Sends CSR to `POST /sign_certificate/` with symmetric key → Receives signed client certificate + CA certificate → Configures Wi-Fi profile.

4. **User connects to Wi-Fi** → Access point forwards EAP-TLS to FreeRADIUS → RADIUS validates client cert against the CA and CRL → Access granted or denied.

5. **Admin revokes a certificate** → Django marks `revoked = True` → Creates a marker in `shared-certs/update_crl/` → `watch_ssids.sh` triggers `process_ssids.sh` → CRL regenerated → Future EAP-TLS attempts with that certificate are rejected.
