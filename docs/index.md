# MyWifiPass System - Technical Documentation

> **Version:** 1.3 &nbsp;|&nbsp; **License:** BSD 3-Clause &nbsp;|&nbsp; **Author:** Pablo Diz de la Cruz

## What is MyWifiPass System?

MyWifiPass System is the server-side component of a Wi-Fi management platform built on **EAP-TLS** authentication. It manages the full lifecycle of X.509 certificates for client devices and integrates with FreeRADIUS to enforce per-user access control.

The typical deployment is at an event or venue: an administrator registers attendees, the system emails each one a Wi-Fi pass (QR code + download link), and before connecting, each user is authorized - either by a **validator** (event staff who checks the user's ID document via the Android app) or by the user themselves via FIDO2/Passkey biometric authentication. Once authorized, the user's device signs a CSR and receives a certificate that grants EAP-TLS Wi-Fi access.

### Technology Stack at a Glance

| Category | Technology |
|---|---|
| Backend | Django 4.2+ / Django REST Framework 3.16 |
| Database | PostgreSQL 15 |
| Web Server | Gunicorn + WhiteNoise |
| PKI / Cryptography | pyOpenSSL, cryptography, pycryptodome |
| RADIUS | FreeRADIUS (containerized) |
| WebAuthn / FIDO2 | `webauthn` library 2.5.0 |
| Containers | Docker Compose (3 services) |
| Mobile Client | MyWifiPass Android (separate repository) |

---

## Table of Contents

1. **[Architecture](architecture.md)** - Component diagrams, EAP-TLS flow, FIDO2 flow, RADIUS file-based integration
2. **[Installation](installation.md)** - Prerequisites, Docker Compose deployment, manual development setup, verification
3. **[Configuration](configuration.md)** - Complete `.env` reference, SMTP setup, FIDO2 custom origins, SSL
4. **[User & Admin Guide](usage.md)** - Admin panel, CSV import, user management, QR codes, email delivery
5. **[API Reference](api-reference.md)** - Full REST API documentation: networks, users, authentication, rate limits, SSE streaming
6. **[FIDO2 / Passkeys](fido2-guide.md)** - Registration, authentication flows, discoverable vs email mode, Android integration
7. **[RADIUS Integration](radius-integration.md)** - File-system sync, shell scripts, SSID lifecycle, CRL automation
8. **[Project Structure](project-structure.md)** - Complete directory tree with explanations
9. **[Development Guide](development.md)** - Local setup, management commands, testing, debugging, CI/CD
10. **[Security Model](security.md)** - Certificate lifecycle, symmetric key protection, CSR validation, token management
11. **[Contributing](contributing.md)** - PR rules, code style, commit conventions, issue templates
12. **[Troubleshooting](troubleshooting.md)** - Common issues: containers, email, RADIUS, certificates, SSL
13. **[Changelog](changelog.md)** - Version history: v1.0 → v1.3, migration guides

---

## Quick Links

- **Swagger UI:** `http://<DOMAIN>/api/swagger`
- **ReDoc:** `http://<DOMAIN>/api/redoc`
- **Django Admin:** `http://<DOMAIN>/admin/`
- **Android App Repository:** [github.com/Pablodiz/mywifipass_android](https://github.com/Pablodiz/mywifipass_android)
- **Main TFG Repository:** [github.com/Pablodiz/TFG_proyecto](https://github.com/Pablodiz/TFG_proyecto)

## Related Repositories

| Repository | Description |
|---|---|
| [mywifipass_android](https://github.com/Pablodiz/mywifipass_android) | Android app for automated network and certificate configuration |
| [TFG_proyecto](https://github.com/Pablodiz/TFG_proyecto) | Complete degree thesis project documentation and overview |

---

> **Copyright (c) 2025, Pablo Diz de la Cruz.**  
> **Copyright (c) 2015, Federico Capoano / OpenWISP (django-x509 original).**  
> Distributed under the [BSD 3-Clause License](../LICENSE).
