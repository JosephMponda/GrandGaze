# MUST–GSL EMR - Code

**Current status**: see `docs/COMPLETED_FEATURES.md` for the maintained,
up-to-date traceability matrix (feature -> brief section -> code location).
That file is the source of truth for "what's done" - everything below this
point is a **historical build log** from the Engineer A/B passes early in
the project and is kept for its debugging detail (the Postgres-specific
bugs below are worth reading), but its own "what's implemented" / "not yet
built" claims are stale: `laboratory`, `imaging`, `pharmacy`, `billing`,
`reporting`, `interop`, `syncapi`, and the Tailwind/HTMX/Alpine frontend
have all since been built. Don't rely on this file alone to judge project
completeness.

Engineer A foundation (`accounts` + `patients`) built per
`docs/backend/engineer-A-core-identity/`. This is the critical-path module -
everyone else's models FK into `Patient`/`User`/`Profile`.

## ⚠️ Reconciliation note (2 July, historical) - read before merging

A parallel pass (pushed to `github.com/JosephMponda/GrandGaze`, described as
Codex-authored) built on top of the zip from the previous session. Diffed it
file-by-file against this working copy and adopted four genuine fixes from
it, plus found and fixed three more by actually exercising the code against
a real Postgres instance (not just sqlite) rather than trusting either
version by inspection:

**Adopted from the external pass:**
1. `EncryptedCharField` wasn't actually forcing its DB column wide enough -
   `kwargs.setdefault(...)` doesn't override an explicit `max_length=64`
   passed by a model field, so ciphertext (much longer than plaintext) could
   get truncated by Postgres. Fixed to force `max_length >= 1024` unconditionally.
2. Missing `pg_trgm` extension migration - `check_possible_duplicate()`'s
   fuzzy matching would `OperationalError` on a fresh Postgres DB with no
   extension enabled. Added `TrigramExtension()` as a migration operation
   (confirmed via Django source it's a no-op on non-Postgres backends, so it
   doesn't break sqlite/CI).
3. `_generate_patient_number()` had a race condition - concurrent
   registrations could generate the same number. Fixed with a locked
   `PatientNumberSequence` row (`select_for_update`).
4. `address_line` wasn't encrypted, despite AGENTS.md §7 listing address as
   PHI. Now uses `EncryptedCharField`. Widening the DB column (fix #1) also
   meant form-level `max_length` no longer enforced real plaintext limits, so
   added explicit `clean_<field>()` validators for national_id/phone/address.

**Found independently, by actually running the full flow against real
Postgres (installed locally to validate, since AGENTS.md mandates it and
sqlite silently hides real bugs - see below):**
5. **Patient-safety bug in my own `register_patient` view**: once *any*
   `confirmed_not_duplicate_of` was posted, the code stopped checking for
   *other* unconfirmed duplicates - a forged or partial confirmation could
   bypass duplicate detection entirely. Fixed to only accept a confirmation
   that matches a real candidate from the actual duplicate set, and still
   blocks if other unconfirmed duplicates remain. Added a regression test.
6. `patient_category` had a model `default` but no `blank=True`, so
   `ModelForm` still required it - a non-browser client (HTMX partial, API)
   omitting it would get silently form-rejected instead of falling back to
   the default. Fixed with `required=False` + a `clean_patient_category()` fallback.
7. `check_possible_duplicate()` combined an annotated queryset
   (`.annotate(similarity=...).order_by("-similarity")`) with a plain one via
   `|` - this doesn't reliably survive further `.filter()`/`.exclude()` calls
   downstream (exactly what the view does). It worked in isolated shell
   tests, then broke immediately on real Postgres the moment the view chained
   a filter on it - `FieldError: Cannot resolve keyword 'similarity'`. Fixed
   by combining matches at the ID-set level (`pk__in=exact_ids | fuzzy_ids`)
   instead of combining heterogeneous querysets directly.

**Why this took installing real Postgres locally, not just trusting sqlite:**
bugs #5 and #7 never showed up in earlier sqlite-based smoke tests - #5
because the assertion logic happened to look plausible in isolation, #7
because sqlite doesn't have `TrigramSimilarity`/`pg_trgm` at all so that code
path was silently skipped, not verified. Once a real Postgres instance was
stood up and the actual `/patients/register/` view was POSTed to with the
real form (not just calling `services.register_patient()` directly), both
surfaced immediately. All 9 tests + a full manual HTTP walkthrough now pass
against real Postgres 16 with `pg_trgm` enabled.

## What's implemented and verified

All Engineer A acceptance criteria (see `docs/backend/engineer-A-core-identity/01_MODULE_SPEC.md` §5)
have been exercised end-to-end against a real DB and pass:

- [x] Role-based login/dashboard for the 8 RBAC groups (`accounts/fixtures/groups_permissions.json`)
- [x] Patient registration with Malawi-context fields, auto-generated `patient_number` (`MUST-YYYYMM-XXXXX`)
- [x] Duplicate detection blocks silent creation; explicit override is logged (`DuplicateConfirmation`)
- [x] Patient search (name / patient number / phone)
- [x] `django-simple-history` audit trail + `/accounts/admin/audit/` viewer (Admin/ICT only - verified 403 for other roles)
- [x] `national_id` / `phone_number` encrypted at rest - verified by reading the raw DB column directly
- [x] 5 failed logins locks the account for 15 min (`django-axes`) - verified via test client, 6th attempt returns 429 even with the correct password

## ⚠️ Two things I changed vs. AGENTS.md as written - read before merging

1. **`django-cryptography` is dropped.** It's unmaintained and hard-incompatible
   with Django ≥5.0 (`ImportError: cannot import name 'baseconv'`). Replaced
   with `core/encrypted_fields.py`, a small Fernet-based field that adds zero
   new dependencies. See `ALLOWED_PACKAGES.md` for the full writeup.
2. **Encrypted fields needed a companion lookup-hash column.** Fernet is
   non-deterministic by design, so `filter(national_id=...)` against the raw
   encrypted column silently never matches - which would have made duplicate
   detection (a patient-safety requirement) quietly do nothing. Fixed by
   storing an HMAC "blind index" (`national_id_lookup`, `phone_number_lookup`)
   and querying that instead. Caught this by actually running the acceptance
   criteria against data, not by inspection - worth the same treatment before
   any other app does exact lookups on an encrypted field (pharmacy/billing
   will want this too).

Everything else matches the original spec as written.

## Running locally

Requires Postgres 16 (see AGENTS.md §2 - do not swap this for sqlite in
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

Run tests (needs Postgres - the model uses `TrigramSimilarity`, Postgres-only):

```bash
python manage.py migrate --run-syncdb  # once
pytest
```

Note: `requirements.txt` (hash-pinned via `pip-compile --generate-hashes`)
isn't generated yet - `requirements.in` is the source of truth for now.
Run `pip-compile --generate-hashes requirements.in` once Postgres/Redis infra
is available to test against, per AGENTS.md §5.3.

## What's implemented - Engineer B (`encounters` + `vitals`)

- Outpatient clinical documentation, sign-and-lock workflow (signed
  encounters are read-only; further notes are addenda, not silent rewrites)
- Patient-level `AllergyRecord` - the exact model/query Pharmacy will use at
  prescribing time via `encounters.services.get_patient_allergies(patient)`
- Vital signs entry with auto-computed BMI and a simplified adult Early
  Warning Score (`vitals/scoring.py` - thresholds documented inline, adult-only)
- Hard-threshold abnormal-vital alerting fires in the same request/response
  cycle via a minimal `reporting.AlertEvent`/`raise_alert()` (the piece of
  Engineer E's module this hard-depends on - not the rest of that scope)
- Dashboard widget ("abnormal vitals, last 4h") registered via the
  `accounts.dashboard_widgets` registry pattern, not hardcoded
- 20 tests total across `patients`/`encounters`/`vitals`, verified against
  real Postgres end-to-end (system checks, migrations, and a full HTTP
  walkthrough - registration → encounter → vitals → alert → dashboard)

## Not yet built (historical, as of this section's original writing)

This list was accurate when Engineer A/B's passes wrapped, and is left here
only for historical context on the build order. It is **not current** -
see `docs/COMPLETED_FEATURES.md` for what's actually built and what's still
open (still-open items as of the last update there: appointment/queue,
inpatient/ward management, emergency triage, nursing documentation, generic
CPOE, dialysis, and inventory - all tracked in that file's "Not Yet Built
(Phase-2 Candidates)" table).
