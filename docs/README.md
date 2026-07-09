# MUST–GSL EMR — Documentation

**Root-level trackers:**
| File | Purpose |
|------|---------|
| `Requirements-Tracker.md` | Every brief spec → implementation status (✅/⚡/❌) |
| `Untouched-Parts.md` | Specifications with zero implementation, prioritized |
| `UI-UX-concerns.md` | Accessibility and usability issues by severity |

---

## Architecture & Standards

| File | Content |
|------|---------|
| `AGENTS.md` | Global stack decisions, module boundaries, security baseline |
| `ALLOWED_PACKAGES.md` | Allowlisted dependencies with justifications |
| `REFERENCE_ALIGNMENT.md` | Comparison to OpenMRS, FHIR, LOINC, DICOM, ICD-11 |

## Security & Compliance

| File | Content |
|------|---------|
| `mfa.md` | MFA integration path (brief §9.4 readiness doc) |
| `Audit.md` | Full security audit with findings, fixes, and judging impact |

## Sprint & Development History

| File | Content |
|------|---------|
| `README.md` (this file) | Documentation index |
| original `README.md` | Historical build log (moved from root) |
| `CHANGES_SUMMARY.md` | Summary of all changes made |
| `FRONTEND_DEBUGGING_GUIDE.md` | Frontend debugging reference |
| `FRONTEND_INTEGRATION.md` | Frontend integration patterns |
| `SESSION_SUMMARY_AND_PHASE2_PLAN.md` | Session summary and phase 2 planning |
| `phase2_rules.md` | Phase 2 engineering rules |
| `ponytail.md` | Known issues and limitations |
| `pipeline-review.md` | CI/CD pipeline review |
| `reference-systems-review.md` | Reference platforms review |
| `sprint-summary-phase-3.md` | Phase 3 sprint summary |

## Phase Specifications

| Path | Content |
|------|---------|
| `phase-2/` | Feature specs for inpatient, emergency, appointments |
| `completed/` | Archived specs, build plans, agent instructions |

## Setup

```bash
cp .env.example .env   # edit DB_* and CRYPTOGRAPHY_KEY
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata accounts/fixtures/groups_permissions.json
python manage.py runserver
```

Tests: `make test` (requires PostgreSQL, or SQLite via `config.test_settings`).

Docker: `make docker-up` (full stack: Django + Postgres + Nginx).

Tailwind: `make tailwind-watch` (compile CSS on changes).
