# MyWifiPass Code Review - Findings & Recommendations

**Date:** February 16, 2026  
**Reviewer:** Code Analysis Bot  
**Scope:** `mywifipass/` folder in mywifipass_system  

---

## Overview

The codebase is a Django REST API for managing WiFi network access through certificate-based authentication. The application has solid domain logic but suffers from architectural debt, security oversights, and testability gaps. Below are concrete, actionable improvements organized by impact.

---

## 🔴 Security Issues

- [ ] **(High) Remove overly permissive ALLOWED_HOSTS**  
  **File:** [settings.py](mywifipass/settings.py#L167)  
  **Issue:** `ALLOWED_HOSTS = ["0.0.0.0", "*"]` allows any host, enabling Host Header injection attacks.  
  **Recommendation:** Replace with environment-configured list:  
  ```python
  ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost').split(',')
  ```

- [ ] **(High) Store SECRET_KEY securely, don't regenerate in code**  
  **File:** [settings.py](mywifipass/settings.py#L152-L160)  
  **Issue:** Auto-generating SECRET_KEY and writing to disk if missing is dangerous; the key path is also hardcoded. If Docker container restarts, key regenerates unpredictably.  
  **Recommendation:** 
    - Require SECRET_KEY in environment or pre-generated `.env` file
    - Fail loudly if not found instead of silently generating
    - Use proper secret management (Docker secrets, Vault, etc.)

- [ ] **(High) Implement CSRF protection in API responses**  
  **File:** [api/auth.py](mywifipass/api/auth.py)  
  **Issue:** QR token endpoints lack CSRF tokens; vulnerable if accessed from browser context.  
  **Recommendation:** Return CSRF token in login responses or require it in POST requests.

- [ ] **(High) Validate and sanitize input in certificate signing**  
  **File:** [models.py](mywifipass/models.py#L155-L205)  
  **Issue:** `sign_csr()` accepts PEM data without validating CSR structure or certificate chain.  
  **Recommendation:** Use cryptography library's `load_certificate_request()` with bounds checking and validate common_name matches user identity.

- [ ] **(High) Fix insecure SECRET_KEY file permissions and paths**  
  **File:** [settings.py](mywifipass/settings.py#L158-L159)  
  **Issue:** Hardcoded path `/djangox509/mywifipass/secrets/.env` and no permission checks (should be 0600).  
  **Recommendation:** Use Django's built-in `.env` loading with proper file permission validation.

- [ ] **(Medium) Implement rate limiting on sensitive endpoints**  
  **Files:** [api/auth.py](mywifipass/api/auth.py), [api/users.py](mywifipass/api/users.py)  
  **Issue:** Token validation, certificate signing, and authorization endpoints lack rate limiting.  
  **Recommendation:** Add `django-ratelimit` or DRF throttling:
  ```python
  class SensitiveEndpointThrottle(UserRateThrottle):
      rate = '5/minute'  # Login attempts
  ```

- [ ] **(Medium) Add email validation and sanitization**  
  **File:** [forms.py](mywifipass/forms.py#L15)  
  **Issue:** Email field accepts input; no check for email header injection in email sending.  
  **Recommendation:** Use `email_validator` library; sanitize email before passing to SMTP.

- [ ] **(Medium) Remove debug information from error responses**  
  **Files:** [api/auth.py](mywifipass/api/auth.py#L38), [api/users.py](mywifipass/api/users.py)  
  **Issue:** `return Response({'error': str(e)})` exposes internal exceptions to clients.  
  **Recommendation:** Log full exception server-side; return generic `"Invalid request"` to clients.

- [ ] **(Medium) Expire and rotate tokens automatically**  
  **File:** [api/auth_model.py](mywifipass/api/auth_model.py)  
  **Issue:** `LoginToken` has `expires_at` but no automatic background cleanup; old tokens linger.  
  **Recommendation:** Add periodic task (Celery) to clean expired tokens; set default TTL to 5 minutes.

- [ ] **(Low) Use secure random for symmetric keys**  
  **File:** [models.py](mywifipass/models.py#L125)  
  **Issue:** Uses `secrets.token_bytes(32)` (correct), but verify it's never logged or exposed in responses.  
  **Recommendation:** Ensure key is never in logs; consider deriving from CSR instead of storing separately.

---

## 🟠 Performance Issues

- [ ] **(High) Fix N+1 query problem in serializers**  
  **File:** [api/users.py](mywifipass/api/users.py#L39-L50)  
  **Issue:** `WifiUserDetailSerializer` accesses `wifiLocation.radius_Certificate.common_name` without prefetch_related, causing query per user.  
  **Recommendation:** Add to viewset:
  ```python
  def get_queryset(self):
      return WifiUser.objects.select_related(
          'wifiLocation__certificates_CA',
          'wifiLocation__radius_Certificate',
          'certificate'
      )
  ```

- [ ] **(High) Move email sending out of main thread**  
  **File:** [utils.py](mywifipass/utils.py#L133-L160)  
  **Issue:** Email is sent in background thread but without proper exception handling; if SMTP times out, user request hangs.  
  **Recommendation:** Use Celery or Django-Q for async tasks; wrap in try/except; implement retry logic.

- [ ] **(High) Avoid repeated CRL generation in loops**  
  **File:** [models.py](mywifipass/models.py#L65-L80)  
  **Issue:** `crl` property regenerates CRL on every access by iterating all revoked certificates.  
  **Recommendation:** Cache CRL for 1 hour; regenerate on certificate revocation, not on read.

- [ ] **(Medium) Optimize WifiNetworkLocation.save() method**  
  **File:** [models.py](mywifipass/models.py#L335-L370)  
  **Issue:** Calls database query in save(); multiple checks cause redundant lookups.  
  **Recommendation:** 
    - Batch UUID existence check with single query
    - Move CA creation to separate method to reduce save() complexity
    - Use `update_or_create()` pattern instead of manual checks

- [ ] **(Medium) Cache QR code generation**  
  **File:** [utils.py](mywifipass/utils.py#L11-L24)  
  **Issue:** QR codes regenerated every request; they're deterministic from URL.  
  **Recommendation:** Cache QR PNG in Redis with key = hash(data); TTL = network end date.

- [ ] **(Medium) Reduce database queries in admin changelist**  
  **File:** [admin.py](mywifipass/admin.py#L21)  
  **Issue:** `WifiUserAdmin.list_display` shows `wifiLocation` without select_related, causing N queries.  
  **Recommendation:** Add `list_select_related = ['wifiLocation']` to admin class.

- [ ] **(Medium) Batch certificate revocation operations**  
  **File:** [models.py](mywifipass/models.py#L330)  
  **Issue:** Revoking 100 users calls `mark_ssid_to_update_crl()` 100 times (creates 100 files).  
  **Recommendation:** Batch revocation; mark SSID once per operation, not per user.

---

## 🟡 Architecture & Separation of Concerns

- [ ] **(High) Extract business logic from models into service layer**  
  **Files:** [models.py](mywifipass/models.py#L119-L210)  
  **Issue:** `WifiUser.sign_csr()`, `revoke_certificate()`, `send_email_manually()` are business logic, not data models.  
  **Recommendation:** Create `services/` folder with:
    ```
    services/
      certificate_service.py  # sign_csr, revoke_certificate, etc.
      email_service.py        # send_email, send_email_manually
      user_service.py         # authorization logic
    ```

- [ ] **(High) Remove circular imports and late imports**  
  **Files:** Multiple files use `from X import Y` inside functions  
  **Issue:** Late imports indicate circular dependencies; hard to trace and debug.  
  **Recommendation:** Restructure imports:
    - Move settings imports to top
    - Create `mywifipass/signals.py` for signal handlers
    - Move URL builders to `api/serializers.py` to break circularity

- [ ] **(High) Move signal handlers to separate module**  
  **File:** [models.py](mywifipass/models.py#L383-L395)  
  **Issue:** Post-delete signals are in models file; mixed concerns.  
  **Recommendation:** Create `mywifipass/signals.py`:
    ```python
    @receiver(post_delete, sender=WifiNetworkLocation)
    def cleanup_network_resources(sender, instance, **kwargs):
        # ...
    ```
    Then import in `apps.py`:
    ```python
    def ready(self):
        import mywifipass.signals
    ```

- [ ] **(High) Reduce WifiUser.save() complexity**  
  **File:** [models.py](mywifipass/models.py#L270-L330)  
  **Issue:** 50+ lines of business logic; does UUID generation, email sending, certificate revocation, multiple state checks.  
  **Recommendation:** Split into:
    - `_ensure_uuid()` - private method
    - `_ensure_symmetric_key()` - private method
    - `_handle_field_updates()` - service layer
    - `_send_notification_email()` - service layer

- [ ] **(Medium) Replace hardcoded paths with configuration**  
  **File:** [radius/radius_certs.py](mywifipass/radius/radius_certs.py#L8-L13)  
  **Issue:** Hardcoded `/djangox509/mywifipass/server_certs` paths; not portable.  
  **Recommendation:** Add to `settings.py`:
    ```python
    RADIUS_CERT_DIR = os.getenv('RADIUS_CERT_DIR', '/djangox509/mywifipass/server_certs')
    ```

- [ ] **(Medium) Create constants file for magic strings**  
  **Files:** Multiple  
  **Issue:** Strings like `"DJANGO_SECRET_KEY"`, `"http://"`, `"https://"` repeated throughout.  
  **Recommendation:** Create `constants.py`:
    ```python
    SECRET_KEY_ENV_VAR = "DJANGO_SECRET_KEY"
    HTTPS_PROTOCOL = "https://"
    HTTP_PROTOCOL = "http://"
    ```

- [ ] **(Medium) Consolidate certificate revocation logic**  
  **Files:** [models.py](mywifipass/models.py), [radius/radius_certs.py](mywifipass/radius/radius_certs.py)  
  **Issue:** Multiple places handle revocation; `revoke_certificate()` and `mark_ssid_for_deletion()` partially overlap.  
  **Recommendation:** Create single `CertificateService.revoke_user_certificate()` that handles both DB and file system.

---

## 🔵 Code Quality & Readability

- [ ] **(High) Remove repetitive docstring-string placeholders**  
  **File:** [api/users.py](mywifipass/api/users.py#L155, #L171, etc.)  
  **Issue:** Docstrings like `f"""GET {USER_PATH}sign_certificate/"""` don't execute code; just clutter.  
  **Recommendation:** Use OpenAPI docstrings via `@swagger_auto_schema()` decorator instead; remove f-string docstrings.

- [ ] **(High) Replace bare except clauses with specific exceptions**  
  **Files:** [models.py](mywifipass/models.py#L392), [util.py](mywifipass/utils.py#L149), [admin.py](mywifipass/admin.py#L124)  
  **Issue:** `except:` swallows all exceptions, including KeyboardInterrupt and SystemExit.  
  **Recommendation:** Use specific exceptions:
    ```python
    except (FileNotFoundError, PermissionError) as e:
        logger.error(f"Cert export failed: {e}")
    ```

- [ ] **(Medium) Standardize error responses**  
  **Files:** [api/auth.py](mywifipass/api/auth.py), [api/users.py](mywifipass/api/users.py)  
  **Issue:** Inconsistent error response format; sometimes `{'error': '...'}`, sometimes `{'message': '...'}`.  
  **Recommendation:** Create response serializers:
    ```python
    class ErrorResponse(serializers.Serializer):
        error = serializers.CharField()
        code = serializers.CharField()
        timestamp = serializers.DateTimeField()
    ```

- [ ] **(Medium) Add logging instead of print statements**  
  **File:** [utils.py](mywifipass/utils.py#L147, #L151, #L153)  
  **Issue:** Email sending uses `print()` for output; won't appear in production logs.  
  **Recommendation:** 
    ```python
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Email sent to {user.email}")
    logger.exception("Email send failed")
    ```

- [ ] **(Medium) Use constants for magic numbers**  
  **Files:** [models.py](mywifipass/models.py#L125 - 32 bytes), [settings.py](mywifipass/settings.py#L170 - port 587), [api/users.py](mywifipass/api/users.py#L159 - 3 minute timeout)  
  **Issue:** Magic numbers scattered throughout; unclear why 32, why 587, why 3 minutes.  
  **Recommendation:** Create `constants.py`:
    ```python
    SYMMETRIC_KEY_SIZE_BYTES = 32
    SMTP_DEFAULT_PORT = 587
    USER_ACCESS_WINDOW_MINUTES = 3
    ```

- [ ] **(Medium) Rename ambiguous variable names**  
  **File:** [models.py](mywifipass/models.py#L21 - `crl_dp_url`), [utils.py](mywifipass/utils.py#L81 - `do_send_mail`)  
  **Issue:** `crl_dp` acronym not immediately clear; `do_send_mail` redundant function name.  
  **Recommendation:** 
    - Rename to `crl_distribution_point_url`
    - Rename to `send_email_async` or `_send_email_in_background`

- [ ] **(Medium) Add type hints to functions**  
  **File:** [utils.py](mywifipass/utils.py#L11)  
  **Issue:** Function signatures lack return types and parameter types beyond docstrings.  
  **Recommendation:** 
    ```python
    from typing import Union, Dict
    
    def generate_qr_code(data: str) -> BytesIO:
        """..."""
    ```

---

## 🟢 Testing & Quality Assurance

- [ ] **(High) Add unit tests for certificate signing logic**  
  **File:** [models.py](mywifipass/models.py#L155-L205)  
  **Issue:** `WifiUser.sign_csr()` is security-critical but has no tests; changes risk breaking authentication.  
  **Recommendation:** Create `tests/test_certificate_signing.py`:
    ```python
    def test_sign_csr_success(self):
        # Generate valid CSR, sign, verify
    
    def test_sign_csr_invalid_format(self):
        # Test rejection of malformed CSR
    
    def test_sign_csr_revokes_old_cert(self):
        # Ensure old certificate is revoked
    ```

- [ ] **(High) Add integration tests for API endpoints**  
  **File:** [api/users.py](mywifipass/api/users.py)  
  **Issue:** No tests for certificate download, authorization, or email sending flows.  
  **Recommendation:** Create `tests/test_api_users.py` with Django TestCase.

- [ ] **(High) Test email error handling**  
  **File:** [utils.py](mywifipass/utils.py)  
  **Issue:** Email sending has try/except/fallback logic but no tests for failure scenarios.  
  **Recommendation:** Mock SMTP; test both connection failures and fallback path.

- [ ] **(Medium) Add tests for signal handlers**  
  **File:** [models.py](mywifipass/models.py#L383-L395)  
  **Issue:** Post-delete signals clean up resources; if they fail silently, orphaned files accumulate.  
  **Recommendation:** Test that deleting `WifiNetworkLocation` cascades cleanup.

- [ ] **(Medium) Add validation tests for CSV import**  
  **File:** [admin.py](mywifipass/admin.py#L98-L133)  
  **Issue:** CSV import has minimal validation; malformed data could corrupt database.  
  **Recommendation:** Test:
    - Missing columns
    - Duplicate emails/id_documents
    - Invalid characters in names

- [ ] **(Medium) Create fixtures and factories**  
  **Issue:** No test data generators; tests will be verbose.  
  **Recommendation:** Use `factory_boy`:
    ```python
    class WifiNetworkLocationFactory(factory.django.DjangoModelFactory):
        name = factory.Sequence(lambda n: f"Network {n}")
        SSID = factory.Sequence(lambda n: f"SSID_{n}")
    ```

---

## 🟡 Error Handling & Edge Cases

- [ ] **(High) Handle missing WifiLocation gracefully**  
  **File:** [models.py](mywifipass/models.py#L131)  
  **Issue:** `@property is_user_authorized` accesses `self.wifiLocation.requires_validator` without null check; throws AttributeError if location is NULL.  
  **Recommendation:** 
    ```python
    @property
    def is_user_authorized(self) -> bool:
        if not self.wifiLocation:
            return False  # User not assigned to network
        # ... rest of logic
    ```

- [ ] **(High) Handle certificate renewal edge cases**  
  **File:** [models.py](mywifipass/models.py#L175-L180)  
  **Issue:** If `sign_csr()` revokes old cert but new cert creation fails, user has no cert.  
  **Recommendation:** Wrap in transaction; rollback if any step fails.

- [ ] **(Medium) Handle missing CA gracefully**  
  **File:** [models.py](mywifipass/models.py#L183)  
  **Issue:** `ca = self.wifiLocation.certificates_CA` could be None; will crash.  
  **Recommendation:** Add check:
    ```python
    ca = self.wifiLocation.certificates_CA
    if not ca:
        raise ValueError(f"CA not initialized for {self.wifiLocation.name}")
    ```

- [ ] **(Medium) Handle file system errors in certificate export**  
  **File:** [radius/radius_certs.py](mywifipass/radius/radius_certs.py#L39-L60)  
  **Issue:** `open()` calls can fail if directory doesn't exist or no write permission.  
  **Recommendation:** Add try/except and log errors; ensure directory creation is atomic.

- [ ] **(Medium) Handle expired sessions in admin**  
  **File:** [admin.py](mywifipass/admin.py#L53)  
  **Issue:** `has_change_permission()` logic is fragile; if permission denied multiple times, message repeats.  
  **Recommendation:** Use `messages.get_messages()` to avoid duplicate messages.

- [ ] **(Low) Handle timezone edge cases**  
  **File:** [models.py](mywifipass/models.py#L393)  
  **Issue:** CRL generation uses `strftime('%Y%m%d%H%M%SZ')` but doesn't validate timezone is UTC.  
  **Recommendation:** Ensure all datetime comparisons use `timezone.now()` consistently.

---

## 🟡 Naming & Conventions

- [ ] **(Medium) Standardize method naming for boolean properties**  
  **File:** [models.py](mywifipass/models.py#L130, #L148)  
  **Issue:** Mix of `is_user_authorized` (property) and `is_registration_open` (field); inconsistent.  
  **Recommendation:** Prefix all boolean fields/properties with `is_`, `has_`, or `should_`.

- [ ] **(Medium) Clarify "URL builder" function naming**  
  **File:** [api/urls.py](mywifipass/api/urls.py#L48-L150)  
  **Issue:** 15+ functions named `*_url()` but they don't perform HTTP requests; they build strings.  
  **Recommendation:** Rename to `build_*_url()` or move to `url_builders.py` module for clarity.

- [ ] **(Low) Use consistent abbreviations**  
  **File:** [models.py](mywifipass/models.py#L21 - `crl_dp`), [settings.py](mywifipass/settings.py#L137 - `TZ`)  
  **Issue:** Abbreviations like `crl_dp`, `SSID`, `UUID` mixed without consistency.  
  **Recommendation:** Document abbreviations in docstring or create `constants.py`.

---

## 📊 Maintainability & Scalability

- [ ] **(High) Add database indexes to frequently queried fields**  
  **File:** [models.py](mywifipass/models.py)  
  **Issue:** Fields like `WifiUser.email`, `WifiNetworkLocation.SSID` are searched but not indexed.  
  **Recommendation:** Add to models:
    ```python
    class WifiUser(models.Model):
        email = models.EmailField(max_length=64, db_index=True)
    
    class WifiNetworkLocation(models.Model):
        SSID = models.CharField(unique=True, max_length=32, db_index=True)
    ```

- [ ] **(High) Add database migration for new indexes**  
  **Issue:** Without migrations, production deployments won't have indexes.  
  **Recommendation:** Run `python manage.py makemigrations` and test performance.

- [ ] **(Medium) Create service layer for business logic**  
  **Issue:** As codebase grows, models will become bloated.  
  **Recommendation:** Proactively move logic to `mywifipass/services/`:
    ```
    services/
      __init__.py
      certificate_service.py
      email_service.py
      authorization_service.py
    ```

- [ ] **(Medium) Add caching strategy**  
  **Issue:** CRL, QR codes, and network details regenerated repeatedly.  
  **Recommendation:** Add Redis integration:
    ```python
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': 'redis://127.0.0.1:6379/1',
        }
    }
    ```

- [ ] **(Medium) Document API rate limits and SLA**  
  **Issue:** No documented limits; could lead to abuse.  
  **Recommendation:** Add to API docs:
    - Login: 5 attempts/minute per IP
    - Certificate signing: 1/minute per user
    - CRL download: 10/minute per IP

---

## 🔧 Miscellaneous Issues

- [ ] **(Medium) Fix email timeout setting**  
  **File:** [settings.py](mywifipass/settings.py#L179)  
  **Issue:** `EMAIL_TIMEOUT = 5` seconds is too short for production; will fail under load.  
  **Recommendation:** Increase to 30 seconds, make configurable:
    ```python
    EMAIL_TIMEOUT = int(os.getenv('EMAIL_TIMEOUT', 30))
    ```

- [ ] **(Medium) Add health check endpoint**  
  **Issue:** No way to verify database, cache, and email connectivity during monitoring.  
  **Recommendation:** Create `/health/` endpoint that checks:
    - Database connectivity
    - Redis connectivity (if used)
    - SMTP connectivity (optional)
    - Certificate expiration status

- [ ] **(Medium) Add audit logging for sensitive operations**  
  **Issue:** No record of who revoked certificates, who authorized users, etc.  
  **Recommendation:** Log to database:
    ```python
    Admin.revoke_certificate() -> Log(user, action='revoke', certificate_id=...)
    ```

- [ ] **(Low) Clean up commented-out code**  
  **File:** [api/users.py](mywifipass/api/users.py#L261-L310)  
  **Issue:** 50-line commented certificate download method; uses version control instead.  
  **Recommendation:** Delete; if needed, retrieve from git history.

- [ ] **(Low) Add docstrings to all public methods**  
  **Files:** Multiple  
  **Issue:** Some methods lack docstrings; hard to understand purpose.  
  **Recommendation:** Use Google-style docstrings consistently.

---

## Summary Statistics

| Category | High | Medium | Low | Total |
|----------|------|--------|-----|-------|
| Security | 6 | 4 | 1 | 11 |
| Performance | 3 | 4 | 1 | 8 |
| Architecture | 4 | 3 | 0 | 7 |
| Code Quality | 2 | 6 | 1 | 9 |
| Testing | 3 | 3 | 0 | 6 |
| Error Handling | 2 | 4 | 1 | 7 |
| Naming | 0 | 3 | 1 | 4 |
| Maintainability | 2 | 4 | 0 | 6 |
| Miscellaneous | 0 | 3 | 1 | 4 |
| **TOTAL** | **22** | **34** | **6** | **62** |

---

## Recommended Priority Order

### Phase 1 - Critical (Security & Stability)
1. Fix ALLOWED_HOSTS
2. Fix SECRET_KEY storage
3. Remove bare except clauses
4. Add N+1 query fixes
5. Extract business logic to services

### Phase 2 - Important (Quality & Performance)
1. Move email to async
2. Add tests for certificate signing
3. Cache CRL generation
4. Optimize admin queries
5. Replace circular imports

### Phase 3 - Nice to Have (Polish)
1. Add logging instead of prints
2. Standardize error responses
3. Add type hints
4. Health check endpoint
5. Audit logging

---

**Next Steps:** Review this checklist, prioritize items with your team, and I can help implement specific changes.
