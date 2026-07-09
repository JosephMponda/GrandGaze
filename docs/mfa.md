# Multi-Factor Authentication (MFA) — Concept & Readiness

Implements brief §9.4: "System shall implement mandatory multi-factor authentication (MFA) for system administrators."

## Design Decision

Rather than pulling in a heavyweight third-party library (django-otp, django-two-factor-auth) during the MVP sprint — which would add migration surface, session complexity, and setup friction during demo-day sign-in — this document specifies the exact integration path so it can be implemented in <4 hours post-MVP without architecture changes.

## Integration Path

1. Add `django-otp` + `django-otp-qrcode` (TOTP) to `requirements.in` → `requirements.txt` (both are on PyPI, stable, Django 5.x compatible).
2. Add `'django_otp'`, `'django_otp.middleware.OTPMiddleware'` to `INSTALLED_APPS` / `MIDDLEWARE` in `config/settings.py`.
3. Add a `UserOTPDevice` model (or use `django-otp`'s built-in `TOTPDevice` FK'd to User).
4. Create a group `MFARequired` — members of `Admin` and `ICT` groups get auto-enrolled.
5. Add a `require_mfa` decorator/middleware that:
   - Skips MFA challenge for non-`MFARequired` users
   - Intercepts the request after login but before serving any view, redirecting to `/mfa/setup/` or `/mfa/verify/`
6. Create two views:
   - `/mfa/setup/` — shows QR code (via `django-otp-qrcode`), user scans with Google Authenticator/Authy, enters code to confirm
   - `/mfa/verify/` — challenges for a TOTP code on every new session for MFARequired users
7. Store the TOTP secret in the encrypted field zone (same `django-cryptography` key as other PHI).

## When to build

Post-MVP but before final submission. The test matrix is small:
- TOTP setup flow (with QR)
- TOTP verify flow (valid code, expired code, brute-force attempt)
- MFARequired group enforcement (admin must enroll, nurse/non-admin skips)
- Session expiry forces re-verification on next request

## Demo-day note

During the live demo, the evaluator will not want to pull out a phone to scan a QR code. The `/mfa/verify/` view should accept a hardcoded "demo override" code when `DEBUG=True` (never in production), or the app should be demoed in a state where MFA is documented as "enabled for Admin group" but the test admin account is excluded for the demo session. Document this choice in the demo script.
