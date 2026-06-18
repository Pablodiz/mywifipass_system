# Installation Guide

## Prerequisites

| Tool | Minimum Version | Notes |
|---|---|---|
| **Docker Engine** | 24.0+ | Must support Compose V2 (`docker compose`, not `docker-compose`) |
| **Git** | 2.30+ | For cloning the repository |
| **Available Ports** | `10000/TCP`, `1812/UDP` | Configurable via `.env` |
| **SMTP Server** | Any (Gmail, SendGrid, Mailgun...) | Required for email delivery of Wi-Fi passes |
| **Domain / Public IP** | Recommended | Required so clients can reach the API and RADIUS |

**Resource requirements (minimum):**
- CPU: 1 core
- RAM: 512 MB (1 GB recommended for production)
- Disk: 2 GB free space (plus database growth)

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/Pablodiz/mywifipass_system.git
cd mywifipass_system
```

---

## Step 2: Configure Environment Variables

```bash
cp .env.example .env
```

Open `.env` in your editor and customize the values. The critical variables are:

### Database (required)

```ini
DB_NAME=mywifipass
DB_USER=mywifipass_user
DB_PASS=your_secure_database_password
```

### Server & Network (required)

```ini
DOMAIN=wifi.yourdomain.com         # Domain or IP:port of the server
SERVER_IP=192.168.1.100             # Server IP address
ALLOWED_HOSTS=wifi.yourdomain.com,192.168.1.100
WEBAPP_PORT=10000                   # Host port for the web app
RADIUS_PORT=1812                    # Host port for RADIUS (UDP)
RADIUS_CLIENT_IP=*                  # Access point IP/subnet, or * for any
SSL=False                           # Enable HTTPS (set to True if using a reverse proxy with SSL)
DEBUG=False                         # Never enable in production
TZ=Europe/Madrid                    # Timezone (affects date calculations)
```

### Email / SMTP (required for Wi-Fi pass delivery)

```ini
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD="your_app_password_16_chars"
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_PORT=587
EMAIL_USE_TLS=True
MYWIFIPASS_FROM_NAME=MyWifiPass
MYWIFIPASS_PLAYSTORE_URL=https://play.google.com/store/apps/details?id=app.mywifipass
```

> **Gmail users:** You must create an [App Password](https://support.google.com/accounts/answer/185833) in your Google Account. Your regular account password will not work.

### FIDO2 / Passkeys (optional)

```ini
# The official app.mywifipass is always included.
# Add custom-compiled apps here if needed:
ANDROID_ADDITIONAL_ORIGINS=
ANDROID_ADDITIONAL_APPS=
```

See [Configuration](configuration.md) for a complete reference of all environment variables.

---

## Step 3: Deploy with Docker Compose

```bash
# Build images and start containers in detached mode
docker compose up -d

# Watch logs in real time
docker compose logs -f

# Check container status
docker compose ps
```

Expected output from `docker compose ps`:

```
NAME             STATUS
mywifipass       Up
radius-server    Up
database         Up (healthy)
```

### What happens on first start?

The `docker-entrypoint.sh` script in the `mywifipass` container runs on every start:

1. Creates the `secrets/` directory if it doesn't exist
2. Generates a `DJANGO_SECRET_KEY` and stores it in `secrets/.env` with `chmod 600` (only if not already present)
3. Runs Django migrations (`makemigrations` + `migrate`)
4. Collects static files (`collectstatic --noinput`)
5. Creates a default superuser: **`admin` / `admin`** (only if no `admin` user exists yet)

> **Security:** Change the `admin` password immediately after your first login at `http://<DOMAIN>/admin/`.

---

## Step 4: Verify the Installation

### Check the Web App

```bash
# Test the API
curl http://localhost:10000/api/networks/

# Test the admin panel
# Open http://localhost:10000/admin/ in your browser
# Login with admin / admin

# Check API documentation
# Open http://localhost:10000/api/swagger in your browser
```

### Check RADIUS

```bash
# Test RADIUS is listening (from the host)
echo | nc -u -w1 localhost 1812 && echo "RADIUS is listening" || echo "RADIUS not reachable"

# Check RADIUS logs
docker compose logs radius
```

### Check Database

```bash
docker compose exec database psql -U mywifipass_user -d mywifipass -c "\dt"
```

---

## Manual Installation (Development)

If you prefer to run without Docker for local development:

### System Requirements

```bash
# Debian/Ubuntu
sudo apt install python3 python3-pip python3-venv postgresql-15 libpq-dev
```

### Setup

```bash
# Clone and create virtual environment
git clone https://github.com/Pablodiz/mywifipass_system.git
cd mywifipass_system
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e .
pip install -r mywifipass/requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your configuration (set DB_HOST=localhost)

# Create PostgreSQL database
sudo -u postgres psql -c "CREATE DATABASE mywifipass;"
sudo -u postgres psql -c "CREATE USER mywifipass_user WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "ALTER DATABASE mywifipass OWNER TO mywifipass_user;"

# Run migrations and create superuser
cd mywifipass
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

> **Note:** When running without Docker, the RADIUS server is not included. For full EAP-TLS testing, use the Docker deployment.

---

## Upgrading

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker compose down
docker compose up -d --build
```

Database migrations are applied by the entrypoint script on container start.

---

## Uninstalling

```bash
# Stop and remove all containers, networks, and volumes
docker compose down -v

# Optionally delete images
docker rmi mywifipass_system-mywifipass mywifipass_system-radius
```

---

## Next Steps

1. **[Configuration](configuration.md)** - Learn about all environment variables
2. **[Usage Guide](usage.md)** - Create your first Wi-Fi network and add users
3. **[Troubleshooting](troubleshooting.md)** - If something doesn't work
