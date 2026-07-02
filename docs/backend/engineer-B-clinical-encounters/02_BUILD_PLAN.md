# Engineer B - Build Plan

## Days 0–2 (Wed 1 – Fri 3 Jul) - Prep while waiting on Engineer A's freeze
You are blocked on `patients.Patient` and `accounts` RBAC helpers, both frozen end of Day 2. Do not wait idle:
- Scaffold `apps/encounters`, `apps/vitals` (empty models, app registered in `INSTALLED_APPS`).
- Write the EWS scoring function (`vitals/scoring.py`) as a **pure function with unit tests using plain dicts**, no model dependency yet - this can be fully built and tested before `Patient` exists.
- Draft the clinical encounter form field list against §8.1.3 and get it reviewed by whoever on the team has clinical-workflow context (a designer, a clinical advisor if you have one) - better to catch a missing field now than after building the UI.

## Day 3 (Mon 6 Jul) - Models
- `Encounter`, `AllergyRecord`, `ClinicalTemplate`, `VitalSignSet`, `EarlyWarningScore` models + migrations, now that `Patient`/`User` are frozen.
- Wire `django-simple-history` onto `Encounter`, `AllergyRecord`, `VitalSignSet`.
- Publish `encounters/services.py` and `vitals/services.py` signatures to the team - **Engineer D (Pharmacy) needs `get_patient_allergies()` by Day 5**, that's your second cross-team contract deadline.

## Days 4–5 (Tue–Wed 7–8 Jul) - Encounter + vitals entry UI
- Encounter creation/edit form, sign-off + addendum flow.
- Vitals entry form with live BMI calc (can be a small Alpine.js computed field, no server round-trip needed for the display-only calc; server recomputes authoritatively on save regardless - never trust the client-side number for what gets stored).
- EWS badge + out-of-range alert wired to `reporting.services.raise_alert()` (coordinate signature with Engineer E by Day 4).

## Day 6 (Thu 9 Jul) - Trends, tabs, dashboard widget
- Vitals trend sparkline/chart on patient profile (Chart.js, see frontend architecture doc).
- Plug "Encounters" and "Vitals" tabs into Engineer A's patient profile template blocks.
- Register the "abnormal vitals" dashboard widget.

## Days 7–9 (Fri 10 – Mon 13 Jul) - Structured templates + polish
- `ClinicalTemplate` seed data for 2–3 common clinic types (general outpatient, dialysis pre-check, antenatal) - cheap win toward "structured templates for common clinics" §8.1.3 and sets up Engineer E's dialysis stretch module to reuse the pattern.
- Cross-test with Engineer D: confirm allergy data flows correctly into prescribing alerts end-to-end.

## Days 10–13 (Tue 14 – Fri 17 Jul) - Bug bash + docs
- Full integration bug bash.
- Write the Clinical Documentation + Vitals section of the System Design Document.
- Tests: signed-record immutability, EWS thresholds at boundary values, allergy cross-module contract.

## Days 14+ - Demo prep
- Rehearse the "abnormal vital fires an alert live" moment and the "signed note can't be silently edited" moment - both are direct Patient Safety (20%) scoring hooks, make sure they're visually obvious in the demo, not buried in a settings screen.

## Dependencies you owe other engineers
- **End of Day 3:** `get_patient_allergies()` signature published - Pharmacy (Engineer D) is blocked on this from Day 5.
- **End of Day 4:** agreed signature for `reporting.services.raise_alert()` with Engineer E.
