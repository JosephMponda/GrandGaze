# Engineer A — AI Agent Instructions

Paste-ready operating rules for Codex / Claude Code when working inside `apps/accounts` and `apps/patients`. Read root `AGENTS.md` first — this file only adds module-specific rules, it doesn't repeat the global ones.

## Scope lock
You own `apps/accounts` and `apps/patients` only. You may add a template block name or a documented hook (e.g. `dashboard_widgets.py` registry entry point) for other apps to use, but you do not implement another engineer's feature "to save time" — that breaks the module boundary the whole team depends on. If a task looks like it needs to touch `apps/encounters`, `apps/laboratory`, `apps/pharmacy`, or `apps/billing`, stop and flag it instead of doing it.

## Do not reinvent (module-specific additions to the root list)
- **Auth**: use `django.contrib.auth.views.LoginView`/`LogoutView`, subclassed only for template/redirect customization. Do not write a custom login view from scratch.
- **RBAC**: use Django `Group`/`Permission` + `@permission_required`. Do not build a custom roles table separate from Django's auth system — `Profile.role` is a convenience label for UI/dashboard purposes, the actual access control is Django Groups.
- **Password handling**: Django's `PASSWORD_HASHERS` default (Argon2 preferred, add `argon2-cffi` to the allowlist request if not present) — never write custom hashing.
- **Fuzzy name matching**: use Postgres `pg_trgm` (`CREATE EXTENSION pg_trgm`) via a migration + Django's `TrigramSimilarity` lookup. Do not pull in a separate fuzzy-matching Python library — this is exactly the kind of extra dependency root `AGENTS.md` §5 tells you to avoid, and Postgres already does it.

## Non-negotiables specific to this module
- Every field in the model spec (`01_MODULE_SPEC.md` §1) that is marked `EncryptedCharField` must actually be encrypted — verify with a raw `psql` query, not just by reading the model definition. Prove it in a test if possible (`assert 'CryptographyField'` behavior or a raw-cursor check that the stored value isn't plaintext).
- `patient_number` generation must be race-safe under concurrent registration (two nurses registering simultaneously must not collide) — use a DB-level sequence or `select_for_update()`, not a naive "count existing rows + 1."
- Duplicate detection is a **blocking** UX step, not a warning toast that can be dismissed without a decision. The registering user must make an explicit choice (confirm new / link to existing) and that choice must be logged with actor + timestamp.
- Never expose `national_id` or full `phone_number` in list views (search results, dashboards) — only in the individual patient detail view, and only to roles with a legitimate need (Clinician, Nurse, Billing, Admin — not, e.g., a generic "LabTech" list view that doesn't need it).

## When generating code, prefer
- Class-based views for CRUD-shaped pages (Django's `ListView`/`DetailView`/`CreateView`/`UpdateView`) over hand-rolled function views, unless the logic is genuinely non-CRUD (e.g. duplicate-detection flow).
- Django `ModelForm` for all data entry — validation lives there, not duplicated in JS.
- Small, focused HTMX partial templates (`_patient_search_results.html`, `_duplicate_warning.html`) returned from dedicated views, not one giant template with conditional includes.

## Test expectations for every PR in this module
- One test per role proving dashboard content differs appropriately.
- One test proving duplicate-detection blocks and logs.
- One test proving encrypted fields aren't stored as plaintext.
- One test proving lockout after 5 failed logins.
- Coverage on `patients/services.py` public functions — these are the contract other engineers build against, they must not regress silently.
