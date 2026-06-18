# Development Guide

This guide covers local development setup, testing, debugging, and contributing to the MyWifiPass System codebase.

---

## Setting Up a Development Environment

### Prerequisites

- Python 3.11+
- PostgreSQL 15 (or Docker for the database only)
- Git
- Virtual environment tool (`venv` or `virtualenv`)

### Full Local Setup

```bash
# Clone the repository
git clone https://github.com/Pablodiz/mywifipass_system.git
cd mywifipass_system

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the package in editable mode
pip install -e .

# Install project-specific dependencies
pip install -r mywifipass/requirements.txt

# Configure environment
cp .env.example .env
# Edit .env: set DB_HOST=localhost and provide DB credentials

# Create PostgreSQL database
sudo -u postgres psql -c "CREATE DATABASE mywifipass;"
sudo -u postgres psql -c "CREATE USER mywifipass_user WITH PASSWORD 'dev_password';"
sudo -u postgres psql -c "ALTER DATABASE mywifipass OWNER TO mywifipass_user;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE mywifipass TO mywifipass_user;"

# Run migrations
cd mywifipass
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start development server
python manage.py runserver 0.0.0.0:8000
```

### Partial Docker Setup (Database Only)

If you want PostgreSQL in Docker but Django locally:

```bash
# Start only the database service
docker compose up -d database

# Update .env: DB_HOST=localhost
# (PostgreSQL container exposes port 5432 by default... 
#  add a ports mapping in docker-compose.yaml if needed)

cd mywifipass
python manage.py runserver
```

---

## Project Architecture for Developers

### Dual Package Structure

The project uses a **two-package** layout:

```
mywifipass_system/          # Root package (installed via setup.py)
├── setup.py                # Package: mywifipass (pip install -e .)
├── django_x509/            # PKI library (fork, installed as sub-package)
└── mywifipass/             # Main Django project
    ├── manage.py           # Django CLI
    └── mywifipass/         # Django app package
        ├── settings.py
        ├── api/            # REST API
        ├── radius/         # RADIUS integration
        └── ...
```

The root `setup.py` installs `django_x509` as a package. The Django project lives at `mywifipass/`.

### Circular Import Management

The codebase uses **lazy imports** to avoid circular dependencies:

```python
# In models.py, imports are done inside methods, not at module level:
def save(self, *args, **kwargs):
    from mywifipass.utils import send_mail  # Import here to avoid circular import
    from mywifipass.radius.radius_certs import export_certificates

def send_email_manually(self):
    from mywifipass.utils import send_mail

# In signals.py, imports are also lazy:
def send_email_on_networks_changed(sender, instance, ...):
    from mywifipass.models import WifiUser
    from mywifipass.utils import send_mail
```

This pattern should be followed for new code that needs to import across module boundaries.

---

## Running Tests

```bash
# Run all Django tests
cd mywifipass
python manage.py test

# Run tests for a specific app
python manage.py test mywifipass
python manage.py test fido2_poc

# Run tests with verbose output
python manage.py test --verbosity=2

# Run a specific test
python manage.py test mywifipass.tests.MyTestClass.test_method
```

### Smoketests

```bash
# Quick smoketest for FIDO2 pages
python test_pages.py
```

---

## Management Commands

### Built-in Django Commands

```bash
python manage.py makemigrations    # Create new migrations
python manage.py migrate           # Apply migrations
python manage.py createsuperuser   # Create admin user
python manage.py shell             # Django interactive shell
python manage.py collectstatic     # Collect static files
python manage.py runserver         # Development server
```

### Custom Commands

```bash
# Cleanup expired login tokens
python manage.py cleanup_expired_tokens
```

---

## Database Migrations

Migrations use Django's built-in migration framework:

```bash
# After changing models:
python manage.py makemigrations

# Check the generated migration:
python manage.py sqlmigrate <app_name> <migration_number>

# Apply:
python manage.py migrate

# Rollback one migration:
python manage.py migrate <app_name> <previous_migration_number>

# Show migration status:
python manage.py showmigrations
```

### Key Migration Notes

- **Migrations 0009–0012** in `mywifipass` changed the `WifiUser` → `WifiNetworkLocation` relationship from 1:N to M:N. This introduced the `networks` ManyToManyField.
- **Migration 0008** added `android_version` to `WifiUser`, which has been **deprecated** but kept for backwards compatibility.

---

## Debugging

### Django Debug Mode

Set `DEBUG=True` in `.env` (never in production).

### Logging

Logs go to stdout (Docker-compatible). Log levels are configurable:

```python
# In settings.py:
_log_level_MYWIFIPASS = 'INFO'
_log_level_FIDO2 = 'DEBUG' if DEBUG else 'INFO'
```

To increase verbosity during development, set `DEBUG=True`.

### Debugging in Docker

```bash
# View Django logs
docker compose logs -f mywifipass

# View RADIUS logs
docker compose logs -f radius

# View database logs
docker compose logs -f database

# Open a shell in the running container
docker compose exec mywifipass bash
docker compose exec radius bash

# Django shell in the container
docker compose exec mywifipass python manage.py shell
```

### Common Debugging Techniques

```python
# In manage.py shell:
from mywifipass.models import WifiUser, WifiNetworkLocation

# Check if a user is authorized
user = WifiUser.objects.get(email="test@example.com")
network = WifiNetworkLocation.objects.first()
print(user.is_authorized_for_network(network))

# Check certificate status
if user.certificate:
    print(user.certificate.revoked)
    print(user.certificate.serial_number)

# Verify CRL
from mywifipass.api.urls import crl_url
print(crl_url(network))

# Test email (from the container)
from mywifipass.utils import send_mail
user = WifiUser.objects.first()
send_mail(user, update=False)
```

---

## CI/CD Pipeline

### GitHub Actions Workflows

| Workflow | File | Trigger | Purpose |
|---|---|---|---|
| CI | `.github/workflows/ci.yml` | Push, PR | Lint, test, build check |
| PyPI | `.github/workflows/pypi.yml` | Release | Publish package to PyPI |
| Version Branch | `.github/workflows/version-branch.yml` | Manual | Create version branches |

---

## Key Libraries and Their Roles

| Library | Version | Purpose |
|---|---|---|
| Django | >=3.2.18, !=4.0.*, <5.2 | Web framework |
| djangorestframework | 3.16.0 | REST API |
| drf-nested-routers | latest | Nested URL routing (networks/users) |
| drf-yasg | latest | Swagger/OpenAPI documentation |
| webauthn | 2.5.0 | FIDO2/WebAuthn server-side verification |
| cryptography | latest | Cryptographic operations |
| pyOpenSSL | latest | X.509 certificate management |
| qrcode | latest | QR code generation |
| Pillow | latest | Image processing (QR, logos) |
| gunicorn | 23.0.0 | WSGI production server |
| whitenoise | latest | Static file serving |
| psycopg2-binary | latest | PostgreSQL database adapter |
| python-decouple | latest | .env file management |

---

## Code Quality

Before submitting a PR:

```bash
# Check for syntax errors
python -m py_compile $(find . -name "*.py" -not -path "./venv/*" -not -path "./.git/*")

# Run all tests
cd mywifipass && python manage.py test

# Verify migrations are up to date
python manage.py makemigrations --check --dry-run
```

---

## Adding New Features

### Adding a New API Endpoint

1. Add the action to the appropriate `ViewSet` in `api/users.py` or `api/networks.py`
2. Decorate with `@action` and specify `permission_classes` and `throttle_classes`
3. Add a URL builder function in `api/urls.py`
4. Add Swagger documentation with `@swagger_auto_schema`
5. Write tests

### Adding a New Model Field

1. Add the field to the model in `models.py`
2. Generate migration: `python manage.py makemigrations`
3. Apply migration: `python manage.py migrate`
4. Update serializers in `api/` if the field should be exposed via API
5. Update admin forms if needed

### Adding a New Configuration Variable

1. Add to `.env.example` with a comment
2. Read in `settings.py` using `os.getenv()` with a sensible default
3. Document in `docs/configuration.md`

---

## Docker Development Tips

### Rebuild a Single Service

```bash
docker compose build mywifipass
docker compose up -d --no-deps mywifipass
```

### Run a One-Off Command in the Container

```bash
docker compose exec mywifipass python manage.py shell
docker compose exec mywifipass python manage.py makemigrations
docker compose exec mywifipass bash
```

### Access the PostgreSQL Shell

```bash
docker compose exec database psql -U mywifipass_user -d mywifipass
```
