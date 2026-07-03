# Engineer C - AI Agent Instructions

Read root `AGENTS.md` first. Scope: `apps/laboratory`, `apps/imaging` only.

## Scope lock
Do not build a second alerting mechanism for critical results - call `reporting.services.raise_alert()` (Engineer E), same as Vitals does. If that function doesn't exist yet when you reach this task, stub a local call to it behind a `try/except ImportError` with a `TODO`, don't invent a parallel `LabAlert` model - that produces exactly the kind of disconnected-alerts problem judges will notice ("why does the dashboard show vitals alerts but not lab alerts?").

## Do not reinvent
- **Barcode rendering**: if you need real barcode generation, request `python-barcode` be added to `ALLOWED_PACKAGES.md` with justification - don't hand-roll barcode encoding logic. If a CSS-only visual placeholder is enough for the demo (it usually is - nobody is scanning it with real hardware), prefer that over adding a dependency at all.
- **Turnaround-time calculation**: this is `resulted_at - created_at`, a Django ORM annotation (`ExpressionWrapper` + `F()`), not a reason to add a reporting/analytics library.
- **Normal-range flagging**: plain comparison against `LabTest.normal_range_low/high` in `save()` or a `pre_save` signal - don't add a rules-engine package for what is a two-line comparison.

## Non-negotiables specific to this module
- **Result verification must be enforced server-side**, not just hidden in the UI - write the check as `if result.entered_by == request.user: raise PermissionDenied` (or equivalent) in the verify view, and test it. A judge asking "what stops someone rubber-stamping their own result" needs a real answer.
- **Critical flags are computed from data, not guessed** - `is_critical` must be derived from `LabTest.is_critical_if_outside_range` and the actual entered value, every time, not left to the user to tick a box manually (a human forgetting to tick a critical-result checkbox is exactly the patient-safety failure mode this feature exists to prevent).
- Do not claim DICOM/PACS integration in any UI copy or documentation - the brief explicitly scopes this to "image-link concept" and "integration-ready design" for MVP. Overclaiming here is a credibility risk with a judging panel that includes clinical/technical reviewers.

## When generating code, prefer
- Django signals (`pre_save`/`post_save`) for the abnormal/critical auto-flagging logic, kept in `laboratory/signals.py` and `imaging/signals.py` respectively - not buried in view code, so it fires consistently regardless of entry point (UI, admin, future API, seed script).
- `services.py` as the only cross-app surface - Pharmacy, Encounters, and Billing should never import `laboratory.models` directly.

## Test expectations for every PR in this module
- Boundary-value tests for abnormal/critical flagging (exactly at range edge, just outside).
- Verification-enforcement test (same user entered+verify → rejected).
- Alert-firing integration test for a critical lab result and a critical imaging finding.
- Turnaround-time calculation correctness test against known timestamps.
