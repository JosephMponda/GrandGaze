# MUST–GSL EMR — Code

Engineer A foundation (`accounts` + `patients`) built per
`docs/backend/engineer-A-core-identity/`. This is the critical-path module —
everyone else's models FK into `Patient`/`User`/`Profile`.

## What's implemented and verified

All Engineer A acceptance criteria (see `docs/backend/engineer-A-core-identity/01_MODULE_SPEC.md` §5)
have been exercised end-to-end against a real DB and pass:

- [x] Role-based login/dashboard for the 8 RBAC groups (`accounts/fixtures/groups_permissions.json`)
- [x] Patient registration with Malawi-context fields, auto-generated `patient_number` (`MUST-YYYYMM-XXXXX`)
- [x] Duplicate detection blocks silent creation; explicit override is logged (`DuplicateConfirmation`)
- [x] Patient search (name / patient number / phone)
- [x] `django-simple-history` audit trail + `/accounts/admin/audit/` viewer (Admin/ICT only — verified 403 for other roles)
- [x] `national_id` / `phone_number` encrypted at rest — verified by reading the raw DB column directly
- [x] 5 failed logins locks the account for 15 min (`django-axes`) — verified via test client, 6th attempt returns 429 even with the correct password

## ⚠️ Two things I changed vs. AGENTS.md as written — read before merging

1. **`django-cryptography` is dropped.** It's unmaintained and hard-incompatible
   with Django ≥5.0 (`ImportError: cannot import name 'baseconv'`). Replaced
   with `core/encrypted_fields.py`, a small Fernet-based field that adds zero
   new dependencies. See `ALLOWED_PACKAGES.md` for the full writeup.
2. **Encrypted fields needed a companion lookup-hash column.** Fernet is
   non-deterministic by design, so `filter(national_id=...)` against the raw
   encrypted column silently never matches — which would have made duplicate
   detection (a patient-safety requirement) quietly do nothing. Fixed by
   storing an HMAC "blind index" (`national_id_lookup`, `phone_number_lookup`)
   and querying that instead. Caught this by actually running the acceptance
   criteria against data, not by inspection — worth the same treatment before
   any other app does exact lookups on an encrypted field (pharmacy/billing
   will want this too).

Everything else matches the original spec as written.

## Running locally

Requires Postgres 16 (see AGENTS.md §2 — do not swap this for sqlite in
committed settings).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # or: pip install -r requirements.in --break-system-packages, for now
cp .env.example .env               # edit DB_* and CRYPTOGRAPHY_KEY

createdb must_emr                  # or point DB_HOST/DB_NAME at Neon
python manage.py migrate
python manage.py loaddata accounts/fixtures/groups_permissions.json
python manage.py createsuperuser
python manage.py runserver
```

Run tests (needs Postgres — the model uses `TrigramSimilarity`, Postgres-only):

```bash
python manage.py migrate --run-syncdb  # once
pytest
```

Note: `requirements.txt` (hash-pinned via `pip-compile --generate-hashes`)
isn't generated yet — `requirements.in` is the source of truth for now.
Run `pip-compile --generate-hashes requirements.in` once Postgres/Redis infra
is available to test against, per AGENTS.md §5.3.

## Not yet built (next up, per AGENTS.md's own module map)

- `encounters`/`vitals` (Engineer B) — depends on this being contract-frozen, which it now is.
- `laboratory`/`imaging` (Engineer C)
- `pharmacy` (Engineer D)
- `billing`/`dialysis`/`reporting`/`interop`/`syncapi` (Engineer E)
- Tailwind CLI + vendored HTMX/Alpine (frontend) — templates currently render
  plain unstyled HTML with `hx-get` attributes wired but no HTMX script
  loaded yet (see `TODO(frontend team)` markers in `templates/base.html`).
- `django-filter`, `drf-spectacular` schema views, and the `interop`
  FHIR-Bundle endpoint are installed/configured but have no views yet — DRF
  is intentionally not used for server-rendered pages per AGENTS.md §3.
