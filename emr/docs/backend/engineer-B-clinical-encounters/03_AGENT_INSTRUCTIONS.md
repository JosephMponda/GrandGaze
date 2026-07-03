# Engineer B — AI Agent Instructions

Read root `AGENTS.md` first. Scope: `apps/encounters`, `apps/vitals` only.

## Scope lock
Do not implement the alerting/notification system — call into `reporting.services.raise_alert()` (Engineer E) once the signature is agreed. Do not implement pharmacy-side allergy checking — you only expose the data via `get_patient_allergies()`, Engineer D consumes it. Duplicating either would create two sources of truth for a patient-safety-critical feature, which is worse than building neither.

## Do not reinvent
- **BMI/EWS calculation**: plain Python functions, no third-party clinical-scoring library. This is deliberately simple arithmetic against a documented threshold table (see module spec §2) — a dependency here would be both unnecessary and harder for judges/auditors to verify than 40 lines of transparent Python.
- **Charting**: use Chart.js as specified in the frontend architecture doc — don't add a Python charting/plotting library for something rendered client-side.
- **Form rendering**: Django `ModelForm`, styled via the shared design system's form partials (ask frontend team for the form-field template snippet rather than writing your own markup from scratch — consistency matters more than module-level cleverness here).

## Non-negotiables specific to this module
- **Signed encounters are immutable in the UI.** Once `signed_by`/`signed_at` are set, the edit view must render an addendum form instead of an in-place edit form. This is a governance requirement, not a UX preference — verify it with a test, not just a manual check.
- **EWS thresholds live in one place** (`vitals/scoring.py` constants dict) — if an agent is asked to "tune" a threshold, it should be a one-line change in that file, never scattered magic numbers in views or templates.
- **Every abnormal-vital alert must actually fire** — this is graded live in the demo. Write an integration test that saves an out-of-range `VitalSignSet` and asserts an `AlertEvent` was created, not just that the scoring function returned the right number.
- Vitals denormalize `patient` onto `VitalSignSet` (not just via `encounter.patient`) specifically so trend queries don't need a join through `Encounter` — don't "clean this up" by removing the FK, it's intentional for query performance on the trend chart.

## When generating code, prefer
- One `services.py` per app as the only cross-app entry point — resist the temptation to import `vitals.models.VitalSignSet` directly from another app; import `vitals.services` instead, even from within this team's own future code, to keep the boundary honest.
- Small pure functions for anything scoring/threshold-related — these are the easiest things to unit test exhaustively and the first thing a judge might ask you to explain.

## Test expectations for every PR in this module
- Boundary-value tests for EWS scoring (just above/below each threshold).
- Immutability test for signed encounters.
- Contract test: `get_patient_allergies()` returns the right records for a patient with 0, 1, and multiple allergies.
- Alert-firing integration test for at least one abnormal vital scenario.
