# Engineer D — Build Plan

## Days 0–2 (Wed 1 – Fri 3 Jul) — Prep while blocked
- Scaffold `apps/pharmacy`.
- Build `Drug` catalog fixture (~30 drugs, WHO Essential Medicines List is a credible, defensible source to draw common entries from — note this in your seed script comments so the choice is traceable).
- Write `pharmacy/safety.py` as **pure functions against plain dicts/dataclasses first**, fully unit-testable before any model exists. This is your highest-value early-investment task — the safety-check logic is your module's core judged feature and needs zero dependency on other apps to build and test the logic itself.

## Day 3–4 (Mon–Tue 6–7 Jul) — Models, wire to real data
- `Prescription`, `DispensingRecord`, `DrugAllergyMap` models + migrations.
- **Hard checkpoint**: confirm `encounters.services.get_patient_allergies()` is live and working (Engineer B commits to this by end of Day 3, per their build plan). If it's not ready, integrate against a stub returning a fixed list, keep building, swap the stub the moment the real function lands — do not block your own progress waiting.
- Wire `pharmacy/safety.py`'s allergy check to the real `AllergyRecord` data.

## Day 5 (Wed 8 Jul) — Prescribing UI + safety UX
- Prescribing form, HTMX-driven safety-check flow (submit → warnings panel → acknowledge/cancel → confirm).
- Override logging (`safety_override_reason` required and validated non-empty when a warning is acknowledged).

## Day 6 (Thu 9 Jul) — Dispensing + queue
- Pharmacist approval/dispensing queue view.
- Dispensing action + workload dashboard widget.

## Days 7–9 (Fri 10 – Mon 13 Jul) — Integration + polish
- Plug "Medications" tab into patient profile.
- Cross-test with Engineer B: allergy recorded in an encounter correctly blocks a later prescription — run this as an actual end-to-end test, not just a code read-through, since it's the single most safety-critical cross-module link in the system.
- Pediatric and pregnancy/renal warning scenarios tested against realistic seed patients.

## Days 10–13 (Tue 14 – Fri 17 Jul) — Bug bash + docs
- Full integration bug bash.
- Write the Pharmacy/Medication Safety section of the System Design Document — be explicit and honest about what's a "concept-level" check (keyword-based allergy matching, simple pediatric dose threshold) versus a production-grade clinical decision support system. Judges will respect honest scoping far more than an overclaim they can poke a hole in.
- Tests: allergy block + override logging, duplicate-therapy warning, pediatric safeguard boundary values.

## Days 14+ — Demo prep
- Rehearse the allergy-block-then-override-with-reason flow as a standalone 60-second demo beat — it's your strongest, most visually clear Patient Safety (20%) moment.

## Dependencies you owe / are owed
- **Owed to you, end of Day 3:** `encounters.services.get_patient_allergies()` from Engineer B — flag immediately in standup if it slips, this is your critical path.
- **You owe Engineer E, by Day 6:** confirm whether Pharmacy needs anything from `billing` (e.g. prescription cost estimate) — if not needed for MVP, say so explicitly so Billing doesn't build an unused hook.
