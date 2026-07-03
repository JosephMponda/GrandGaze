# Engineer C - Build Plan

## Days 0–2 (Wed 1 – Fri 3 Jul) - Prep while blocked
Blocked on `patients.Patient` and `encounters.Encounter` (the latter frozen Day 3, per Engineer B's plan). Use the time to:
- Scaffold `apps/laboratory`, `apps/imaging`.
- Build the `LabTest`/`ImagingModality` catalogs as fixtures - this needs zero dependency on other apps and can be fully seeded now (research realistic Malawi-relevant test panels: FBC, malaria RDT, HIV rapid test, creatinine, glucose, urinalysis, pregnancy test - these read as clinically credible to judges).
- Draft barcode generation approach: use `python-barcode` (request allowlist addition - small, single-purpose, well-maintained, generates an SVG/PNG, no network calls) or, if you want zero new dependency, render a Code128-style pattern as pre-styled `<div>` bars in the template - decide by Day 2 and note the choice in your PR.

## Day 3 (Mon 6 Jul) - Models
- `LabOrder`, `LabResult`, `ImagingRequest`, `ImagingReport` models + migrations once `Encounter` is frozen.
- Wire `django-simple-history`.
- Publish `laboratory/services.py` and `imaging/services.py` signatures.
- Agree the `raise_alert()` signature with Engineer B and Engineer E jointly - you're the third consumer, make sure it's not shaped only around vitals.

## Days 4–5 (Tue–Wed 7–8 Jul) - Order + result entry
- Lab order form, specimen collection flow with barcode render.
- Result entry with auto abnormal/critical flagging.
- Two-person verification enforcement (`entered_by != verified_by`, checked server-side, tested).

## Day 6 (Thu 9 Jul) - Imaging + workload dashboard
- Imaging request form with pregnancy-status safety gate.
- Imaging report entry.
- Lab workload dashboard (pending/resulted counts, turnaround-time calc).

## Days 7–9 (Fri 10 – Mon 13 Jul) - Tabs, alerts, polish
- Plug "Labs"/"Imaging" tabs into patient profile.
- Confirm critical-result alerts actually reach the dashboard alert widget (cross-test with Engineer E).
- Second lab test panel/imaging modality if time allows (stretch, only after MVP acceptance criteria all pass).

## Days 10–13 (Tue 14 – Fri 17 Jul) - Bug bash + docs
- Full integration bug bash.
- Write the Diagnostics section of the System Design Document, including the honest LOINC-readiness statement (populated where known, explicitly blank elsewhere - don't overstate coverage to judges).
- Tests: abnormal/critical flagging boundary values, verification-enforcement, alert-firing.

## Days 14+ - Demo prep
- Rehearse: order a test → collect → enter a critical result → alert appears live on the dashboard. This single flow touches Clinical Relevance, Patient Safety, and Technical Design scoring rows in about 90 seconds - make it the centerpiece of your part of the demo.

## Dependencies you owe other engineers
- **End of Day 6:** confirm to Engineer D that `AllergyRecord`-style safety patterns (their allergy checks) and your critical-result alerts both funnel through the same `reporting.services.raise_alert()` so the dashboard shows one unified alert feed, not three disconnected ones.
