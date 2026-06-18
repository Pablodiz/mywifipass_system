# Project Structure

```
mywifipass_system/
│
├── .devcontainer/
│   └── devcontainer.json              # VS Code dev container configuration
│
├── .env.example                       # Template for environment variables
├── .gitignore
│
├── .github/                           # GitHub configuration
│   ├── dependabot.yml                 # Automated dependency updates
│   ├── ISSUE_TEMPLATE/                # Issue templates (bug, feature, question)
│   ├── pull_request_template.md       # PR checklist template
│   └── workflows/                     # CI/CD pipelines
│       ├── ci.yml                     # Continuous integration
│       ├── pypi.yml                   # PyPI publishing
│       └── version-branch.yml         # Version branch management
│
├── docker-compose.yaml                # Docker Compose orchestration (3 services)
├── Dockerfile_mywifipass              # Main webapp Docker image (python:3.13-slim-bullseye)
│
├── django_x509/                       # PKI library (fork of OpenWISP django-x509)
│   ├── __init__.py                    # Package version: 1.3.0
│   ├── admin.py                       # CA and Cert admin registration
│   ├── apps.py
│   ├── base/
│   │   ├── __init__.py
│   │   ├── admin.py                   # Abstract CA/Cert admin classes
│   │   └── models.py                  # AbstractCa, AbstractCert - core PKI logic (569 lines)
│   ├── models.py                      # Concrete Ca, Cert models (swappable via django-swapper)
│   ├── settings.py                    # Defaults: 2048-bit RSA, SHA-256, 365-day validity
│   ├── migrations/                    # 9 database migration files
│   ├── static/                        # Static assets
│   ├── templates/                     # Django templates
│   └── tests/                         # Library tests
│
├── mywifipass/                        # ★ Main Django project
│   ├── docker-entrypoint.sh           # Container startup: secret key, migrations, superuser
│   ├── manage.py                      # Django management CLI
│   ├── requirements.txt               # Project Python dependencies
│   ├── prueba.py                      # Experimental/test script
│   │
│   ├── mywifipass/                    # ★ Main Django app
│   │   ├── __init__.py
│   │   ├── settings.py                # Global configuration (DB, REST, email, throttling, SSL...)
│   │   ├── urls.py                    # Root URLconf (web, admin, API, FIDO2, assetlinks)
│   │   ├── wsgi.py                    # WSGI entry point (Gunicorn)
│   │   ├── asgi.py                    # ASGI entry point
│   │   │
│   │   ├── models.py                  # MyCustomCA, MyCustomCert, WifiUser, WifiNetworkLocation (560 lines)
│   │   ├── admin.py                   # Django Admin with custom actions (QR, email, revoke, CSV import)
│   │   ├── views.py                   # Web views: network list, details, registration, admin QR
│   │   ├── forms.py                   # WifiUserForm (email validation), CSVImportForm
│   │   ├── utils.py                   # QR generation, email sending (inline QR via Content-ID)
│   │   ├── signals.py                 # Signal handlers: token cleanup, auto-email on M2M change
│   │   │
│   │   ├── api/                       # ★ REST API module
│   │   │   ├── __init__.py
│   │   │   ├── urls.py                # Nested router + URL builder helper functions
│   │   │   ├── users.py               # WifiUserViewSet (591 lines): CRUD, CSR signing, download, QR, SSE
│   │   │   ├── networks.py            # WifiNetworkLocationViewSet: CRUD + CRL endpoint
│   │   │   ├── auth.py                # QR token authentication endpoint
│   │   │   ├── auth_model.py          # LoginToken model (UUID, 5-min expiry)
│   │   │   └── throttles.py           # 5 rate limiters (login, CSR, auth, download, validation)
│   │   │
│   │   ├── radius/                    # ★ RADIUS integration
│   │   │   └── radius_certs.py        # Certificate export, SSID deletion/CRL markers
│   │   │
│   │   ├── management/commands/       # Custom Django management commands
│   │   │   └── cleanup_expired_tokens.py
│   │   │
│   │   ├── migrations/                # 14 database migration files
│   │   ├── templates/                 # Django templates (web pages, admin, emails)
│   │   │   └── mywifipass/
│   │   │       ├── common/            # Shared template components
│   │   │       ├── email/
│   │   │       │   └── register_email.html
│   │   │       ├── wifilocation/      # Network list and detail templates
│   │   │       └── wifiuser/          # User registration and confirmation templates
│   │   ├── static/                    # Static files (CSS, images)
│   │   └── tests/                     # Test directory
│   │
│   ├── fido2_poc/                     # ★ FIDO2/WebAuthn sidecar app
│   │   ├── __init__.py
│   │   ├── admin.py                   # Admin registration for FIDO2 models
│   │   ├── apps.py
│   │   ├── config.py                  # RP ID, RP name, origins from env vars (106 lines)
│   │   ├── models.py                  # PasskeyCredential, AuthenticationChallenge, Fido2NetworkConfig (184 lines)
│   │   ├── views.py                   # Registration and authentication start/finish + assetlinks (544 lines)
│   │   ├── urls.py                    # /fido2/register/*, /fido2/authenticate/*
│   │   ├── serializers.py
│   │   ├── signals.py                 # FIDO2-related signal handlers
│   │   ├── android_dal.py            # Android Digital Asset Links JSON generator
│   │   ├── templates/                 # FIDO2 HTML pages
│   │   ├── static/
│   │   ├── migrations/                # 3 database migration files
│   │   └── docs/                      # FIDO2-specific documentation
│   │       └── README.md
│   │
│   ├── secrets/                       # Django secret key storage (gitignored)
│   ├── server_certs/                  # RADIUS certificate export directory (Docker volume mount point)
│   └── tests/                         # Project-level tests
│
├── our_radius/                        # ★ FreeRADIUS container configuration
│   ├── .gitignore
│   ├── Dockerfile                     # FreeRADIUS image with cron + inotify-tools + scripts
│   ├── RADIUS_SECRET/
│   │   └── secret.txt                 # RADIUS shared secret
│   └── config/
│       ├── docker-entrypoint.sh       # Generates RADIUS secret if missing
│       ├── cron                       # Crontab for automation scripts
│       ├── default                    # FreeRADIUS default site config
│       ├── eap-template               # EAP module template per SSID
│       ├── server-template            # Virtual server template per SSID
│       ├── clients.conf.template      # RADIUS client (AP) configuration template
│       ├── watch_ssids.sh             # ★ inotify watcher - triggers process_ssids.sh on file events
│       ├── process_ssids.sh           # Main orchestrator: add/remove SSIDs, update CRLs
│       ├── create_ssids.sh            # Add SSID to FreeRADIUS
│       ├── remove_ssids.sh            # Remove SSID from FreeRADIUS
│       ├── update_crl.sh              # Regenerate CRL for an SSID
│       ├── automatic_crl_update.sh    # Periodic CRL refresh (via cron, every 12h)
│       └── normalize_ssid.sh          # SSID name normalization utility
│
├── docs/                              # ★ This documentation
│   ├── index.md
│   ├── architecture.md
│   ├── installation.md
│   ├── configuration.md
│   ├── usage.md
│   ├── api-reference.md
│   ├── fido2-guide.md
│   ├── radius-integration.md
│   ├── project-structure.md
│   ├── development.md
│   ├── security.md
│   ├── contributing.md
│   ├── troubleshooting.md
│   └── changelog.md
│
├── wip_docs/                          # Work-in-progress documents (internal)
│   ├── BUGS_ACTUALES.md
│   ├── CHANGELOG_SECURITY.md
│   ├── CODE_REVIEW.md
│   ├── fido2_integration_plan.md
│   ├── fido2_integration.md
│   ├── IMPLEMENTATION_PROGRESS.md
│   ├── RESUMEN_CAMBIOS_2026-04-06_ANDROID_SYSTEM.md
│   ├── RESUMEN_FEATURE_FIDO2_SYSTEM.md
│   └── SSE_AUTHORIZATION_MIGRATION_PLAN.md
│
├── dont_push/                         # Gitignored miscellaneous files
│   ├── MyWifiPass_logo.png
│   ├── funciona_wifi.html
│   ├── github.io.html
│   ├── portal_evento.html
│   └── tools/
│       └── render_email_preview.py
│
├── customization/                     # Customization hooks (empty - for future use)
│   ├── configuration/django/
│   └── theme/
│
├── setup.py                           # Python package setup (name='mywifipass')
├── requirements.txt                   # Base Python dependencies
├── test_pages.py                      # Smoke test for FIDO2 pages
├── README.md                          # Project overview and quick start
├── user_manual.md                     # English user manual for administrators
├── LICENSE                            # BSD 3-Clause License
└── DOCUMENTATION.md                   # Single-file documentation, predates docs/
```

---

## Key Files by Responsibility

### PKI & Cryptography
| File | Lines | Role |
|---|---|---|
| `django_x509/base/models.py` | 569 | CA/Cert generation, signing, importing, extensions, revocation |
| `mywifipass/mywifipass/models.py` | 560 | Custom CA/CRL, network-aware cert creation, CSR validation and signing |

### API
| File | Lines | Role |
|---|---|---|
| `mywifipass/mywifipass/api/users.py` | 591 | Full user CRUD + custom actions (CSR, download, QR, SSE authorization streaming) |
| `mywifipass/mywifipass/api/urls.py` | 184 | Nested router + 14 URL builder functions |
| `mywifipass/mywifipass/api/networks.py` | 115 | Network CRUD + CRL public endpoint |
| `mywifipass/mywifipass/api/throttles.py` | 62 | 5 rate limiters per IP/user |

### RADIUS Integration
| File | Lines | Role |
|---|---|---|
| `mywifipass/mywifipass/radius/radius_certs.py` | 95 | Export certs + mark for deletion/CRL update |
| `our_radius/config/process_ssids.sh` | 101 | Main orchestrator script |
| `our_radius/config/create_ssids.sh` | - | FreeRADIUS virtual server generator |

### FIDO2
| File | Lines | Role |
|---|---|---|
| `mywifipass/fido2_poc/views.py` | 544 | Registration and authentication flows |
| `mywifipass/fido2_poc/models.py` | 184 | Passkey storage, challenge management, network config |
| `mywifipass/fido2_poc/config.py` | 106 | RP configuration from environment |

### Infrastructure
| File | Lines | Role |
|---|---|---|
| `mywifipass/mywifipass/settings.py` | 314 | Global Django configuration |
| `docker-compose.yaml` | 82 | Service orchestration |
| `mywifipass/docker-entrypoint.sh` | 31 | Container startup automation |

---

## Data Flow Through the Codebase

```
User registration (web/API)
    │
    ▼
forms.py / api/users.py       ← validates input
    │
    ▼
models.py (WifiUser.save)     ← generates UUID, symmetric key, sends email
    │
    ▼
utils.py                       ← renders email, generates QR, sends via SMTP thread
    │
    ▼
Android app scans email QR → download/ returns symmetric key + URLs
    │
    ▼
api/users.py (download)        ← returns Wi-Fi pass data including symmetric key
    │
    ▼
api/users.py (sign_certificate) ← validates CSR, verifies symmetric key
    │
    ▼
models.py (WifiUser.sign_csr)  ← creates and signs X.509 certificate
    │
    ▼
radius/radius_certs.py         ← exports server certs to shared volume
    │
    ▼
our_radius/config/*.sh         ← configures FreeRADIUS, manages certs/CRLs

[Admin QR login flow - separate from the above]
api/auth.py                    ← exchanges admin QR token for DRF auth token
```
