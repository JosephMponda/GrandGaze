# Phase 2 — Feature Development

> Next-sprint features mapped from the MUST–GSL EMR Innovation Challenge Brief.
> Each feature folder follows the same structure: `01_FEATURE_SPEC.md`,
> `02_BUILD_PLAN.md`, `03_AGENT_INSTRUCTIONS.md`.

## Feature Priority Queue

| Priority | Feature | Brief Section | Dependencies |
|---|---|---|---|
| **P0** | Admission & Ward Management (Inpatient) | §8.1.4 | Encounter (built), Patient (built) |
| **P0** | Emergency & Triage Module | §8.1.5 | Patient (built), Vitals (built) |
| **P1** | Appointment Scheduling & Queue | §8.1.2 | Patient (built) |
| **P1** | Nursing Documentation | §8.1.6 | Patient (built), Encounter (built) |
| **P1** | Inventory & Stock Management | §8.1.15 | Pharmacy (built), Laboratory (built) |
| **P2** | Dialysis & CKD Module | §8.1.12 | Patient (built) |
| **P2** | Generic CPOE (Order Sets) | §8.1.9 | Encounter (built), Lab (built), Pharmacy (built) |
| **P2** | Maternal / Child Health | §8.2.3 | Patient (built), Encounter (built) |
| **P3** | Theatre & Anaesthesia | §8.2.2 | Patient (built) |
| **P3** | Full PACS / Imaging Storage | §8.2.1 | Imaging (built) |
| **P3** | Research & Teaching Tools | §8.2.9–10 | Patient (built), de-identified export |
| **P3** | Advanced Clinical Decision Support | §8.1.17 | Pharmacy safety (built), Vitals EWS (built) |

## Guiding Principles (same as Phase 1)

See `AGENTS.md` for the full stack decisions. Key Phase 2 rules:

1. **No SPA frameworks** — server-rendered Django + HTMX + Alpine + Tailwind
2. **No new dependencies** without allowlist entry in `ALLOWED_PACKAGES.md`
3. **`django-simple-history`** on every new clinical/PHI model
4. **`core/encrypted_fields.py`** for any new PII/PHI fields
5. **RBAC on every view** via `@login_required` + `@role_required`
6. **Every new app** registered in `config/settings.py` + `config/test_settings.py` + `config/urls.py`
7. **Tests**: happy path + permission-denied + validation-failure for every new view
8. **Dashboard widgets** registered via `accounts.dashboard_widgets`, not hardcoded
9. **Patient profile tabs** registered as HTMX partials, not full-page redirects
10. **Offline-first**: syncapi endpoint + service worker pattern maintained

## Template for Feature Spec

Each feature folder (`docs/phase-2/<feature-name>/`) contains:

- `01_FEATURE_SPEC.md` — Data model, services interface, views, acceptance criteria
- `02_BUILD_PLAN.md` — Implementation order, dependencies, milestones
- `03_AGENT_INSTRUCTIONS.md` — Module-specific AI agent rules, non-negotiables
