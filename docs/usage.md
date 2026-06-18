# Usage Guide

This guide covers day-to-day operations for administrators managing Wi-Fi networks and users through the MyWifiPass System.

---

## Accessing the Admin Panel

Navigate to `http://<DOMAIN>/admin/` and log in with your credentials. The default superuser is `admin` / `admin` - **change this immediately**.

The admin panel provides access to:
- **WiFi Networks** - Create and manage EAP-TLS networks
- **WiFi Clients** - Manage end users
- **Passkey Credentials** - View registered FIDO2 passkeys
- **FIDO2 Network Configs** - Enable/disable FIDO2 per network
- **Certificate Authorities** - View generated CAs
- **Certificates** - View individual user/server certificates

---

## Managing Wi-Fi Networks

### Creating a Network

1. Go to **WiFi Networks → Add**
2. Fill in the required fields:

| Field | Description |
|---|---|
| **Name** | Descriptive name (e.g. "TechConf 2026") |
| **SSID** | Exact network identifier (e.g. `TechConf2026`) |

3. Optional fields:

| Field | Description |
|---|---|
| **Location** | Physical venue (e.g. "Main Auditorium") |
| **Description** | Full description visible to users |
| **Brief description** | Short summary for email/QR displays |
| **Start date / End date** | Network validity period. Certificates expire at `end_date` 23:59:59 |
| **Form link** | Optional external registration form URL |
| **Logo** | Event image displayed on the web and in emails |

4. Configure behavior flags:

| Flag | Default | Effect |
|---|---|---|
| **Is enabled in RADIUS** | True | When enabled, exports certificate configuration to FreeRADIUS. When disabled, removes it |
| **Is visible in web** | True | Shows the network on the public networks list (`/networks/`) |
| **Is registration open** | True | Allows users to self-register via the web form |
| **Requires validator** | True | Requires admin authorization (via admin panel or FIDO2 passkey) before users can obtain certificates |
| **Send emails automatically** | True | Sends emails automatically when users register or are assigned to the network |

### What Happens When You Save a Network

1. A **Certificate Authority (CA)** is created with validity matching the network's dates
2. A **RADIUS server certificate** is generated and exported to `shared-certs/pending/`
3. The RADIUS container's `watch_ssids.sh` (inotify watcher) detects the new files and configures FreeRADIUS
4. The CA's CRL distribution point URL is embedded in all certificates issued for this network

### Disabling a Network

Uncheck **Is enabled in RADIUS** and save. The system will:
- Mark the SSID for deletion in `shared-certs/deletion/`
- The RADIUS container will remove the virtual server configuration

### Deleting a Network

Deleting a network from the admin panel triggers a `post_delete` signal that:
1. Deletes the associated CA
2. Marks the SSID for deletion from RADIUS
3. Revokes the RADIUS server certificate

---

## Managing Wi-Fi Users (Clients)

### Creating a Single User

1. Go to **WiFi Clients → Add**
2. Fill in:

| Field | Description |
|---|---|
| **Name** | User's full name (max 64 chars) |
| **Email** | Valid email address (used for Wi-Fi pass delivery) |
| **ID document** | Optional identifier (e.g. DNI, passport number) |
| **Networks** | Select one or more networks the user can access |

3. The system will:
   - Generate a 32-byte symmetric key for certificate protection
   - Assign a UUID to the user
   - If `send_emails_automatically = True` on any assigned network, send a registration email with QR and download link

### Bulk Import via CSV

1. Go to **WiFi Clients** and look for the CSV import section
2. Prepare a CSV file with headers: `name, email, id_document, networks`
3. Example:

```csv
name,email,id_document,networks
Juan Pérez,juan@example.com,12345678A,TechConf 2026
María López,maria@example.com,87654321B,TechConf 2026
Carlos Ruiz,carlos@example.com,11223344C,TechConf 2026
```

4. File restrictions:
   - Max size: 5 MB
   - Must have `.csv` extension
   - `id_document` is optional
   - `networks` must match existing network names

### User States and Actions

Each user has status flags visible in the admin list:

| Flag | Meaning |
|---|---|
| **Has downloaded pass** | User has downloaded their Wi-Fi pass. Cannot download again |
| **Has attended** | User has been authorized at least once. The `/validate/` check-in scan returns 403 if already set; the admin can still re-authorize via `/authorize/` directly |
| **Email sent** | The registration email was sent |
| **Allow access expiration** | If set, user has a temporary window to sign a CSR (set by FIDO2 authentication or by admin via authorize action) |

### Admin Actions on Users

| Action | Description |
|---|---|
| **Send email** | Resends the Wi-Fi pass email with QR code |
| **Revoke certificate** | Invalidates the user's certificate and updates all relevant CRLs |
| **Show QR code** | Displays the user's Wi-Fi pass QR code (the same one sent in the registration email) |

### User Self-Registration

If a network has `is_registration_open = True` and `is_visible_in_web = True`:

1. Users visit `http://<DOMAIN>/networks/<uuid>/register`
2. They enter name, email, and optionally ID document
3. The form validates:
   - Email format and length (max 64 chars)
   - No SMTP header injection characters
   - No duplicate emails in the same network
   - Name length (2–64 characters)
4. On success, if `send_emails_automatically = True`, a Wi-Fi pass email is sent

---

## Email Delivery

### What the Email Contains

Each Wi-Fi pass email includes:

- **Inline QR code** - Embedded via Content-ID (`cid:qr_wifi_pass`), displayed inline in the HTML version
- **Direct download URL** - Unique per user, one-time use (blocked after `has_downloaded_pass = True`)
- **Play Store link** - To download the MyWifiPass Android app
- **Network metadata** - Name, location, description, dates

### Sending Emails Manually

From the admin panel, select a user and click the **Send email** button. You can also do this programmatically:

```python
from mywifipass.models import WifiUser

user = WifiUser.objects.get(email="user@example.com")
success, message = user.send_email_manually()
print(message)  # "Emails sent successfully" or error message
```

### Auto-Send Behavior

When `send_emails_automatically = True`:
- Emails are sent when a user is saved (created or updated if name/email changed)
- Emails are also sent via the `post_add` signal on the M2M networks relationship (covers the case where an admin assigns networks to an existing user via Django Admin)

Emails are sent from a **background thread** to avoid blocking the HTTP response.

---

## QR Codes

### Admin QR Code

The **Admin QR** (accessible at `/admin/qr/`) encodes a JSON object:

```json
{
  "username": "admin",
  "token": "550e8400-e29b-41d4-a716-446655440000",
  "url": "http://wifi.example.com/api/login/token"
}
```

The Android admin app scans this QR to obtain a short-lived `LoginToken` (5-minute expiry), which is exchanged for a DRF auth token at `POST /api/login/token`.

### User QR Code

The user's QR code is generated from the download URL and sent in the registration email. It encodes:

```
https://pablodiz.github.io/mywifipass?url=http://<DOMAIN>/api/networks/<uuid>/users/<uuid>/download/
```

This redirects through a GitHub Pages landing page for a better user experience on mobile devices.

---

## FIDO2 / Passkey Validation

### Enabling FIDO2 for a Network

1. Go to **FIDO2 Network Configs → Add**
2. Select the network
3. Check **Requires FIDO2**
4. Save

Setting `requires_fido2 = True` also sets `requires_validator = True` on the network. Users must be authorized (via FIDO2 self-validation or admin QR → authorize flow) before they can sign a CSR.

### FIDO2 Authorization Workflow (User Self-Validates)

1. The user opens `http://<DOMAIN>/fido2/authenticate/` in their browser (or the Android app triggers the flow)
2. They click **Authenticate**
3. The browser/Android Credential Manager presents available passkeys for this domain
4. The user selects their passkey and provides biometric/PIN
5. On success, the user gets a **3-minute authorization window** (`allow_access_expiration = now + 3 min`)
6. During this window, the user's Android app can call `POST /sign_certificate/`

### Passkey Registration (One-Time per User)

Users must register a passkey first at `http://<DOMAIN>/fido2/register/`. This associates a WebAuthn credential with their email in the `PasskeyCredential` model. Once registered, the user can self-authorize at `/fido2/authenticate/` or via the Android Credential Manager.

See [FIDO2 Guide](fido2-guide.md) for the complete technical flow.

---

## Web Views

| URL | Description |
|---|---|
| `/` | Redirects to `/networks/` |
| `/networks/` | Lists all visible networks with logos, descriptions, and registration links |
| `/networks/<uuid>/` | Detailed view of a single network |
| `/networks/<uuid>/register` | User self-registration form |
| `/networks/<uuid>/confirmation` | Confirmation page after successful registration |
| `/fido2/register/` | FIDO2 passkey registration page |
| `/fido2/authenticate/` | FIDO2 authentication/validation page |

---

## Management Commands

### Cleanup Expired Tokens

```bash
docker compose exec mywifipass python manage.py cleanup_expired_tokens
```

Removes expired `LoginToken` entries. Recommended to run as a cron job:

```bash
# Example crontab on the host (every hour)
0 * * * * cd /path/to/mywifipass_system && docker compose exec -T mywifipass python manage.py cleanup_expired_tokens
```

---

## Next Steps

1. **[API Reference](api-reference.md)** - Programmatic access to all functionality
2. **[FIDO2 Guide](fido2-guide.md)** - Deep dive into passkey authentication
3. **[RADIUS Integration](radius-integration.md)** - Understand the RADIUS synchronization
