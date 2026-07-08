# Sprint Summary - Phase 2 (Jul 2–4, 2026)

## Built this sprint

### Emergency & Triage (§8.1.5)
- `TriageEncounter` model with CTAS categories (5-level)
- Rapid registration - minimal patient + triage in one step
- Severity-sorted queue view
- Triage resolution (discharged/admitted/referred/dead)
- Patient profile tab + dashboard widget
- 12 tests

### Inventory / Stock Management (§8.1.15)
- `StockLevel` model tied to `Drug` (OneToOneField)
- Stock check + adjustment services
- Dispense guard - blocks if stock = 0, deducts on success
- `/pharmacy/stock/` management UI with add-form + levels table
- Stock badges on queue page + dashboard widget

### Dialysis & CKD (§8.1.12)
- New `dialysis` app - CKD staging, dialysis prescribing, session recording
- Auto-calculated fluid removal from pre/post weight
- Missed session heuristic (naive weekday checker)
- Patient tab, session log, today's dashboard
- Dashboard widget + 8 tests

### Inpatient / Ward Management (§8.1.4)
- New `inpatient` app - Ward, Bed, Admission, WardRoundNote models
- Full admit/transfer/discharge workflow with bed assignment
- Color-coded ward bed board (`/inpatient/ward/<id>/`)
- Inpatient dashboard with occupancy cards
- Patient tab, Admit button on profile, dashboard widget
- 11 tests

### Bug fixes
- `services.models.TriageEncounter` → direct model import (circular import)
- Rapid-register crash: imported `_generate_patient_number()`, wrapped in `@transaction.atomic`
- Patient search: split query into tokens for multi-word matching
- Template `_stock` → `stock` (Django forbids underscore-prefixed attributes)

## Stats
- 98 tests pass, 1 skipped (pg_trgm Postgres-only)
- 19 new test files across 4 modules
- ~1,500 lines added (models, services, views, templates, tests)
- 0 new external dependencies

## State
- All users: `nurse1`, `clinician1`, `pharmacist1`, `labtech1`, `radiog1`, `billing1`, `admin1`, `ict1` / `test123`
- 5 patients seeded, patient #4 has documented penicillin allergy, patient #5 admitted to Medical Ward
- Seed data flushes cleanly via `--flush`
