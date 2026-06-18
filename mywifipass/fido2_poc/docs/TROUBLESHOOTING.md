# Troubleshooting

## Android App Integration

### Issue: App can't verify FIDO2

Check:
1. SHA256 hash extraction is correct (no typos, proper format with colons)
2. `ANDROID_ADDITIONAL_APPS` is valid JSON syntax
3. Domain matches what app was compiled with
4. Certificate configuration is deployed in `ANDROID_ADDITIONAL_APPS`

Debug:
```bash
# Check assetlinks is serving
curl https://your-domain/.well-known/assetlinks.json | jq .

# Verify your package appears
curl https://your-domain/.well-known/assetlinks.json | jq '.[] | .target.package_name'

# Check server logs
docker logs mywifipass-app | grep -i android
```

Verify SHA256 extraction:
```bash
keytool -list -v -keystore your.jks | grep SHA256 | tr -d ' '
```

Then format with colons and add to `.env`:
```bash
ANDROID_ADDITIONAL_APPS=[{"package_name":"com.yourapp","sha256":"AA:BB:CC:DD:..."}]
```

### Issue: assetlinks.json returns 404

The endpoint should always exist. If it returns 404:
- Check Django is running
- Run: `curl http://localhost:8000/.well-known/assetlinks.json`
- Check logs: `docker logs mywifipass-app`

## Admin Interface

### Issue: FIDO2 Config checkbox doesn't appear for new network

After creating a new network in Django Admin:
- Save the network first
- Refresh the page
- The checkbox should appear under "FIDO2 Config" section

Or directly in inline edit:
- When creating new network, you should see "FIDO2 Config" row
- Check "Requires FIDO2"
- Return to main network form and save

If still not appearing:
- Check docker logs: `docker logs mywifipass-app | grep fido2`
- Verify `fido2_poc` is in `INSTALLED_APPS`

### Issue: Enabling FIDO2 doesn't auto-activate requires_validator

This is a post_save signal. It should activate immediately.

Check:
```bash
# In Django shell
docker exec mywifipass-app python manage.py shell
>>> from mywifipass.models import WifiNetworkLocation
>>> n = WifiNetworkLocation.objects.get(name="YourNetwork")
>>> n.fido2_config.requires_fido2
>>> n.requires_validator
```

Both should be True if FIDO2 is enabled.

If not working, check logs for signal errors:
```bash
docker logs mywifipass-app | grep -i signal
```

## Configuration

### Issue: ANDROID_ADDITIONAL_APPS syntax error

Ensure valid JSON:
```bash
# Invalid (single quotes)
ANDROID_ADDITIONAL_APPS=[{'package_name':'com.app','sha256':'AA:BB:...'}]

# Valid (double quotes)
ANDROID_ADDITIONAL_APPS=[{"package_name":"com.app","sha256":"AA:BB:..."}]
```

Test JSON validity:
```bash
python3 -m json.tool <<< 'YOUR_JSON_HERE'
```

Multiple apps:
```bash
ANDROID_ADDITIONAL_APPS=[
  {"package_name":"com.app1","sha256":"AA:BB:..."},
  {"package_name":"com.app2","sha256":"CC:DD:..."}
]
```

### Issue: Changes to .env not taking effect

Restart the container:
```bash
docker compose restart mywifipass-app
```

Changes to environment variables are read at startup.

## General

### Getting Logs

```bash
# All FIDO2-related logs
docker logs mywifipass-app | grep -i fido2

# Android-related logs  
docker logs mywifipass-app | grep -i android

# Last 50 lines
docker logs mywifipass-app | tail -50

# Follow logs in real-time
docker logs -f mywifipass-app
```

### Verify Installation

```bash
# Check fido2_poc is installed
docker exec mywifipass-app python manage.py shell
>>> from fido2_poc import models
>>> from fido2_poc import config
>>> print(config.EXPECTED_ORIGINS)
```

Should print RP origins including android:apk-key-hash entries.
