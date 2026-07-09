# ALLOWED_PACKAGES.md

Per AGENTS.md §5: no new dependency without an entry here first, with a one-line justification.

| Package | Justification |
|---|---|
| django (>=5.2,<6.0) | Core framework, LTS. |
| djangorestframework | Offline-sync/FHIR-lite/dashboard JSON endpoints only. |
| django-filter | DRF filtering - explicitly allowlisted exception in AGENTS.md §5.2. |
| psycopg[binary] | Postgres driver. |
| django-simple-history | Audit trail on every clinical/PHI model. |
| django-axes | Account lockout after 5 failed logins. |
| drf-spectacular | OpenAPI docs on the DRF surface. |
| gunicorn | WSGI server for deployment. |
| whitenoise | Static file serving without a separate CDN/node pipeline. |
| redis | Cache / session store / Celery broker (week 2). |
| python-decouple | Env-based settings, no secrets in code. |
| pip-audit | CI dependency vulnerability scan. |
| pytest, pytest-django, factory-boy | Test suite. |
| django-otp (>=1.7) | TOTP-based multi-factor authentication for admin/ICT roles (§9.4). |
| qrcode (>=8.0) | Generate TOTP provisioning QR codes for authenticator app setup. |
| Pillow | Image library required by qrcode for PNG output. |

## Removed from the original AGENTS.md allowlist

- **`django-cryptography`** - REMOVED. It is unmaintained (last release years
  ago) and hard-incompatible with Django >=5.0: it imports
  `django.utils.baseconv`, which Django removed in 5.0. `manage.py check`
  fails immediately with `ImportError: cannot import name 'baseconv'`.

  Replacement: `core/encrypted_fields.py` - a ~40-line `EncryptedCharField`
  built directly on `cryptography.fernet`. This adds **zero new packages**:
  `cryptography` is already pulled in transitively by `django-axes`. This is
  the AGENTS.md §5.2 instruction taken literally ("prefer what's already
  available over a new package") applied to the field-encryption problem
  itself, not just to auth/sessions/forms.

  If the team would rather pin `Django<5.0` to keep `django-cryptography`
  working as originally specified, or adopt a different field-encryption
  package, raise it - this was a build-blocking substitution made to keep
  the Day-2 contract-freeze on schedule, not a unilateral architecture change.
