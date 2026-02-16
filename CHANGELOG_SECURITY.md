# CHANGELOG - Security Hardening

> Tracking security fixes applied to mywifipass folder

## Format
- **[CODE]** - Brief description
- Status: ✅ Done | 🔄 In Progress | ⏳ Pending
- Commit: git hash (or pending)

---

## Security Issues

| Code | Description | Status | Commit |
|------|-------------|--------|--------|
| SEC-1 | Remove overly permissive ALLOWED_HOSTS | ⏳ Pending | - |
| SEC-2 | Store SECRET_KEY securely (fail loudly) | ⏳ Pending | - |
| SEC-3 | Add CSRF token to API login responses | ⏳ Pending | - |
| SEC-4 | Validate CSR structure and certificate chain | ⏳ Pending | - |
| SEC-5 | Fix SECRET_KEY file permissions & hardcoded paths | ⏳ Pending | - |
| SEC-6 | Implement rate limiting on sensitive endpoints | ⏳ Pending | - |
| SEC-7 | Email validation & sanitization | ⏳ Pending | - |
| SEC-8 | Remove debug info from error responses | ⏳ Pending | - |
| SEC-9 | Token auto-expiry & cleanup task | ⏳ Pending | - |
| SEC-10 | Verify secure random for symmetric keys | ⏳ Pending | - |

---

## Related Items
- Performance: PERF-1, PERF-2, PERF-3, PERF-6
- Architecture: ARCH-5, ARCH-6
- Code Quality: CODE-1, CODE-2, CODE-4

---

> Updated: 2026-02-16
