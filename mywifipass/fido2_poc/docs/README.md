# FIDO2 PoC Documentation

This folder contains documentation for the FIDO2 passkey authentication proof-of-concept.

## Quick Start

1. **[CONFIGURATION.md](CONFIGURATION.md)** - Environment variables and setup
2. **[OVERVIEW.md](OVERVIEW.md)** - How it works and architecture
3. **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions
4. **[TESTING.md](TESTING.md)** - Instructions on how to run tests on the FIDO2 implementation

## Summary

FIDO2 enables passwordless authentication using biometric/security key verification. When enabled on a network:

- Users register a passkey via their phone/computer
- On successful authentication, a 3-minute CSR signing window opens
- User can request certificate during this window
- Network admin approval is handled automatically

## Key Points

- Completely isolated POC in `fido2_poc/`
- Minimal non-invasive modifications to core `mywifipass/` (API serializers and URL mapping)
- Configuration via `.env` only
- No static files (everything generated at runtime)
- Can be removed without breaking the main application

## Admin Interface

Enable FIDO2 per network:
1. Django Admin → WiFi Networks
2. Open/create a network
3. Check "Requires FIDO2" in FIDO2 Config section
4. Save (requires_validator auto-activates)

## Adding Custom Android Apps

Update `.env`:
```bash
ANDROID_ADDITIONAL_APPS=[{"package_name":"com.yourapp","sha256":"AA:BB:CC:..."}]
```

Restart container:
```bash
docker compose restart mywifipass-app
```

The official app is always included automatically.
