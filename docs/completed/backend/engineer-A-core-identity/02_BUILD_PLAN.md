# Engineer A - Build Plan

Calendar dates below assume kickoff **Wed 1 Jul 2026**, per the root `README.md` timeline. You are the critical path - every other engineer is blocked on your contract freeze at end of Day 2.

## Day 0 (Wed 1 Jul) - Repo & environment
- Create GitHub org repo, branch protection on `main` (require PR + 1 review + CI green).
- Django project scaffold: `config/` (settings split: `base.py`/`local.py`/`production.py`), `apps/accounts`, `apps/patients`.
- `docker-compose.yml`: Postgres 16, Redis, Django dev server. This is also the seed of the local-fallback bundle Engineer E will finish later.
- `requirements.in` seeded with the allowlist from root `AGENTS.md` §5. `pip-compile` to generate hashed `requirements.txt`.
- CI skeleton: GitHub Actions running `pytest`, `pip-audit`, `ruff`/`flake8` on every PR.
- `django-simple-history`, `django-axes`, `django-cryptography` installed and wired into `settings.base`.

## Day 1 (Thu 2 Jul) - Auth & RBAC
- `Profile` model + migration, groups fixture (8 roles), signal to auto-create `Profile` on `User` creation.
- Login/logout views styled against the frontend design system (coordinate with frontend team - this is the first page they'll style, use it as the template pattern for the rest of the app).
- Session timeout config, `django-axes` lockout config.
- `accounts/permissions.py` - the `has_role()` / `require_role()` helpers every other app will import. **Publish this file's interface in the team Slack/standup today** - engineers B–E need it by Day 3.

## Day 2 (Fri 3 Jul) - Patient model + FREEZE
- `Patient`, `NextOfKin`, `PatientMergeRecord`, `ReferralRecord` models + migrations.
- `patients/services.py` public interface implemented per module spec §3.
- **Contract freeze**: post the final field list and `services.py` signatures to the team. Any change after this point goes through the "tag all 4 engineers" PR process in root `AGENTS.md` §4.
- Seed script: 500 synthetic patients (Faker, Malawi locale approximations for names/villages) for realistic demo data and search-performance testing.

## Days 3–4 (Mon–Tue 6–7 Jul) - Registration & search UX
- Registration form + duplicate-detection flow (pg_trgm similarity + exact ID/phone match).
- HTMX live search partial.
- Patient profile page shell with empty tab placeholders - hand these template block names to Engineers B–E so they know exactly where their HTMX partials plug in.

## Days 5–6 (Wed–Thu 8–9 Jul) - Dashboard & audit viewer
- Role-based dashboard shell + `dashboard_widgets.py` registry pattern, documented for other engineers to register into.
- Audit trail viewer (`/admin/audit/`) wrapping `django-simple-history`, restricted to Admin/ICT.
- Write the `dashboard_widgets.py` registry doc snippet and drop it in the shared team channel - this is a second cross-team contract point.

## Days 7–9 (Fri 10 – Mon 13 Jul) - Hardening & integration support
- Merge/duplicate-patient workflow UI.
- Support other engineers integrating their tabs/widgets into your shell pages - expect PR reviews and small fixes, not new features, from here.
- Write tests: registration happy path, duplicate-block path, permission-denied paths per role, lockout test.

## Days 10–13 (Tue 14 – Fri 17 Jul) - Bug bash + submission support
- Full-team integration bug bash (all engineers, cross-testing each other's modules).
- Security pass: confirm encrypted fields are actually encrypted in the DB, confirm default-deny on every view.
- Contribute to System Design Document (§19.1 of brief) for the Identity/MPI section - you own writing this part since you own the module.

## Days 14+ - Demo prep
- Prepare the "possible duplicate detection" and "role-based access" moments specifically for the live demo - these are direct, visible Patient Safety (20%) and Clinical Governance points, make sure they're rehearsed, not just present in code.

## Dependencies you owe other engineers (do not slip these)
- **End of Day 1:** `accounts/permissions.py` interface.
- **End of Day 2:** `Patient` model frozen + `patients/services.py`.
- **End of Day 6:** `dashboard_widgets.py` registry pattern + patient-profile tab template block names.
