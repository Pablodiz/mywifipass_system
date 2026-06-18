# Troubleshooting

Common issues and their solutions when deploying or operating the MyWifiPass System.

---

## Containers

### Containers don't start

```bash
docker compose logs mywifipass
docker compose logs radius
docker compose logs database
```

**Common causes:**

| Problem | Solution |
|---|---|
| Port already in use | Change `WEBAPP_PORT` or `RADIUS_PORT` in `.env` |
| Database connection refused | Verify `DB_PASS` in `.env` and that PostgreSQL started (`docker compose ps database`) |
| `.env` not found | Ensure `.env` exists in the project root: `cp .env.example .env` |
| Docker daemon not running | `sudo systemctl start docker` |
| Permission denied on volumes | `sudo chown -R 1000:1000 shared-certs/` (if bind mounts used) |

### Container keeps restarting

```bash
# Check the exit code and logs
docker compose ps
docker compose logs --tail=100 mywifipass
```

Common causes: database connection failure, missing environment variables, syntax error in `.env`.

---

## Email

### Emails not being sent

1. **Verify SMTP credentials:**
   ```bash
   docker compose exec mywifipass python -c "
   import os
   print('HOST:', os.getenv('EMAIL_HOST'))
   print('USER:', os.getenv('EMAIL_HOST_USER'))
   print('PASS set:', bool(os.getenv('EMAIL_HOST_PASSWORD')))
   "
   ```

2. **Test SMTP connectivity:**
   ```bash
   docker compose exec mywifipass python -c "
   import smtplib
   try:
       s = smtplib.SMTP('smtp.gmail.com', 587, timeout=5)
       s.starttls()
       print('SMTP connection OK')
       s.quit()
   except Exception as e:
       print(f'SMTP error: {e}')
   "
   ```

3. **Gmail-specific issues:**
   - Ensure you're using an **App Password** (not your account password)
   - 2-Step Verification must be enabled on the Google Account
   - App passwords are 16 characters with no spaces

4. **Check if emails are being triggered:**
   ```bash
   docker compose logs mywifipass | grep -i "email\|send_mail"
   ```

5. **Send a test email:**
   ```python
   docker compose exec mywifipass python manage.py shell
   >>> from mywifipass.models import WifiUser
   >>> user = WifiUser.objects.first()
   >>> if user:
   ...     success, msg = user.send_email_manually()
   ...     print(msg)
   ```

---

## RADIUS

### RADIUS not authenticating clients

1. **Verify the RADIUS secret matches:**
   ```bash
   cat our_radius/RADIUS_SECRET/secret.txt
   # Must match what's configured on the access point
   ```

2. **Check the access point IP is allowed:**
   ```bash
   # .env
   RADIUS_CLIENT_IP=*
   # Or specify the exact IP/subnet: RADIUS_CLIENT_IP=192.168.1.0/24
   ```

3. **Check RADIUS logs for errors:**
   ```bash
   docker compose logs radius | tail -50
   ```

4. **Verify certificates are properly exported:**
   ```bash
   docker compose exec radius ls -la /etc/raddb/server_certs/processed/
   # Should have a directory for each active SSID
   docker compose exec radius ls -la /etc/raddb/sites-enabled/
   # Should have server config files for each SSID
   ```

5. **Check if FreeRADIUS is running:**
   ```bash
   docker compose exec radius pgrep freeradius
   ```

6. **Test RADIUS from the host:**
   ```bash
   echo | nc -u -w1 localhost 1812 && echo "RADIUS port open" || echo "RADIUS port closed"
   ```

### Certificates not syncing to RADIUS

1. **Check the shared volume:**
   ```bash
   docker compose exec mywifipass ls -la /djangox509/mywifipass/server_certs/pending/
   # New SSIDs should appear here after saving a network
   ```

2. **Check the inotify watcher is running:**
   ```bash
   docker compose exec radius pgrep -f watch_ssids
   ```

3. **Manually trigger SSID processing:**
   ```bash
   docker compose exec radius bash /usr/local/bin/process_ssids.sh
   ```

4. **Check the SSID-specific logs:**
   ```bash
   docker compose exec radius cat /etc/raddb/server_certs/logs/<SSID>.log
   ```

### CRL Not Updating

1. **Check if the update marker exists:**
   ```bash
   docker compose exec radius ls -la /etc/raddb/server_certs/update_crl/
   # Should have files named after revoked SSIDs
   ```

2. **Verify the CRL endpoint returns valid data:**
   ```bash
   curl http://localhost:10000/api/networks/<uuid>/crl/
   ```

3. **Check that the certificate was actually revoked:**
   ```python
   docker compose exec mywifipass python manage.py shell
   >>> from mywifipass.models import MyCustomCert
   >>> cert = MyCustomCert.objects.first()
   >>> print(cert.revoked, cert.revoked_at)
   ```

---

## Certificates

### CSR signing fails

1. **Check if user is authorized:**
   ```python
   user = WifiUser.objects.get(email="...")
   network = WifiNetworkLocation.objects.get(...)
   print(user.is_authorized_for_network(network))
   ```

2. **If `requires_validator = True`:**
   - The `check_user_authorized` SSE stream checks `allow_access_expiration` (must be a future datetime)
   - `allow_access_expiration` is set by FIDO2 passkey authentication OR by an admin via `POST /authorize/` (both open a 3-minute window)
   - Note: `sign_certificate` itself does not enforce `allow_access_expiration` server-side; enforcement is in the client SSE flow

3. **Verify the symmetric key:**
   - The `token` parameter in the CSR request must match `user.certificates_symmetric_key.hex()`
   - The key is provided in the Wi-Fi pass download JSON

4. **Check CSR format:**
   - Must be valid PEM: starts with `-----BEGIN CERTIFICATE REQUEST-----`
   - Must be self-signed (verified by the server)
   - Common Name (CN) must match user's name or email

### User can't download Wi-Fi pass

1. **Check `has_downloaded_pass`:**
   ```python
   user = WifiUser.objects.get(email="...")
   print(user.has_downloaded_pass)  # True means already downloaded
   ```
   - To reset: set `has_downloaded_pass = False` and save

2. **Verify the URL:**
   ```python
   from mywifipass.api.urls import wifipass_download_url
   print(wifipass_download_url(user))
   ```

---

## Database

### Migration errors

```bash
# Show migration status
docker compose exec mywifipass python manage.py showmigrations

# Force re-run a specific migration
docker compose exec mywifipass python manage.py migrate <app> <migration> --fake

# Reset and start fresh (destroys all data!)
docker compose down -v database
docker compose up -d
```

### Database connection issues

```bash
# Test connection from webapp container
docker compose exec mywifipass python -c "
import psycopg2
conn = psycopg2.connect(
    dbname='mywifipass',
    user='mywifipass_user',
    password='your_password',
    host='database'
)
print('Connected OK')
conn.close()
"
```

---

## Web App

### 500 Internal Server Error

1. **Enable DEBUG temporarily:**
   ```ini
   # .env
   DEBUG=True
   ```
   ```bash
   docker compose restart mywifipass
   ```
   > **Disable DEBUG after troubleshooting!**

2. **Check Django logs:**
   ```bash
   docker compose logs mywifipass | grep -i error
   ```

### Static files not loading (404 on CSS/JS)

```bash
docker compose exec mywifipass python manage.py collectstatic --noinput
docker compose restart mywifipass
```

### Admin QR code not displaying

1. Verify you're logged in to `/admin/` (requires session auth)
2. Navigate to `/admin/qr/` - should return a PNG image
3. Check for errors:
   ```bash
   docker compose logs mywifipass | grep -i "admin_qr\|LoginToken"
   ```

---

## FIDO2 / WebAuthn

### Registration fails

1. **Check domain configuration:**
   ```bash
   docker compose exec mywifipass python -c "
   from fido2_poc.config import RP_ID, RP_NAME, ORIGIN, EXPECTED_ORIGINS
   print(f'RP_ID: {RP_ID}')
   print(f'ORIGIN: {ORIGIN}')
   print(f'EXPECTED_ORIGINS: {EXPECTED_ORIGINS}')
   "
   ```

2. **Common issues:**
   - `RP_ID` does not match the browser's domain (must be the registrable domain, no port)
   - Not using HTTPS (browsers require HTTPS for WebAuthn, except `localhost`)
   - User already has an active passkey

### Authentication fails

1. **Check if the passkey exists:**
   ```python
   from fido2_poc.models import PasskeyCredential
   cred = PasskeyCredential.objects.filter(wifi_user__email="...").first()
   print(cred.is_active, cred.last_used)
   ```

2. **Challenge may have expired:**
   - Challenges expire after 5 minutes
   - Retry the authentication flow from `/start`

---

## SSL / HTTPS

### Mixed content warnings

If using a reverse proxy with SSL termination:

```ini
# .env
SSL=True
```

The Django app will use `https://` for absolute URLs (emails, QR codes, etc.).

### Redirect loops

If behind a reverse proxy, ensure the proxy sets the `X-Forwarded-Proto` header. The Django app uses:

```python
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

---

## Performance

### Slow responses

1. **Check database query performance:**
   ```python
   docker compose exec mywifipass python manage.py shell
   >>> from django.db import connection
   >>> from django.db.utils import reset_queries
   >>> # Check query count on a specific operation
   ```

2. **Increase Gunicorn workers:**
   Edit `Dockerfile_mywifipass` and increase the `--workers` flag:
   ```dockerfile
   gunicorn --bind 0.0.0.0:8000 --workers=6 mywifipass.wsgi:application
   ```

### Certificate generation is slow

CSR signing involves RSA operations. The rate limit is set to 3/minute per user. For high-volume scenarios, consider:
- Reducing key size (not recommended for security)
- Using ECDSA instead of RSA (requires code changes to `django_x509/base/models.py`)

---

## Getting Help

If you can't resolve an issue:

1. Search [existing issues](https://github.com/Pablodiz/mywifipass_system/issues)
2. Open a new issue with:
   - Full error logs
   - `.env` configuration (redact passwords)
   - Steps to reproduce
   - Environment details (Docker version, OS, etc.)
