# GrandGaze — Session Summary & Phase-2 Plan

**Date:** 3 July 2026 · **Reviewed by:** Claude (senior-engineer pass) · **Status:** Phase 1 verified and fixed, ~1 week to submission

---

## 1. What this session was

A senior-engineer review of the MUST–GSL EMR codebase against `AGENTS.md` and the project's own tracking docs — not a read of the docs, but actually cloning the repo, running `manage.py check`, running the real test suite, running `pip-audit`, and tracing through the patient-safety-critical code paths line by line. Three real issues were found and fixed; all changes are pushed to `main`.

## 2. What was verified as genuinely solid

- Full module set implemented and tested: `accounts`, `patients`, `encounters`, `vitals`, `laboratory`, `imaging`, `pharmacy`, `billing`, `reporting`, `interop`, `syncapi`.
- RBAC (8 groups), Fernet field encryption + HMAC lookup-hash pattern, `django-simple-history` audit trail, sign-and-lock encounters, EWS scoring, FHIR-Bundle export, offline sync scaffolding (service worker + IndexedDB + `syncapi`), Docker Compose local fallback.
- Frontend actually built (vendored HTMX/Alpine/Tailwind CLI, zero CDN, zero npm) — contrary to what the (now-fixed) README claimed.
- `pip-audit` clean on the real dependency tree.
- Duplicate-patient detection (`patients/services.py`) and critical-lab-result alerting (`laboratory/models.py`) both traced through correctly — the ID-set combination fix and forged-confirmation-ID block from the earlier reconciliation note are implemented right and match their tests.

## 3. Issues found and fixed this session

| # | Issue | Where | Fix | Status |
|---|---|---|---|---|
| 1 | `AXES_FAILURE_LIMIT` had silently drifted from 5 to 10 (added alongside a since-reverted demo-login-buttons feature, never reverted with it) — violates AGENTS.md §7's explicit "5 failed logins locks the account" | `config/settings.py` | Reset to 5 | ✅ Pushed |
| 2 | `accounts` app (owns login/RBAC/lockout) had **zero automated tests** — exactly how #1 went unnoticed | `accounts/tests.py` | New file: lockout regression test + happy/validation paths | ✅ Pushed |
| 3 | `README.md` / `CHANGES_SUMMARY.md` flatly contradicted the actual code (claimed labs/pharmacy/billing/interop/syncapi/frontend "not yet built" when all were implemented and tested) | `README.md`, `CHANGES_SUMMARY.md` | Marked as historical, pointed to `docs/COMPLETED_FEATURES.md` as the one live status doc | ✅ Pushed |
| 4 | **Critical patient-safety bug**: `check_prescription_safety()` computes `critical` vs `warning` levels but nothing downstream ever branched on it — a documented penicillin allergy could be bypassed by typing any text into the override-reason box, identical to overriding a "you already have an active prescription" notice. Directly contradicted the project's own claim in `docs/COMPLETED_FEATURES.md` §9.2 ("critical blocks submit") | `pharmacy/services.py`, `pharmacy/views.py`, `pharmacy/safety.py` | New `CriticalSafetyBlock` exception, enforced at the service layer (the real public interface — confirmed `seed_demo.py` calls it directly) and the view layer; template updated so a blocked prescription shows no dead-end override UI | ✅ Pushed |
| 5 | Fixing #4 broke the demo seed script — it had a scripted scenario using the *old* bypass (amoxicillin prescribed over a documented penicillin allergy via a typed reason) | `core/management/commands/seed_demo.py` | Reworked into a real demo: attempt is correctly blocked, system falls back to ceftriaxone (a real penicillin-safe alternative per the drug-allergy map). Verified by actually running the seed command end-to-end | ✅ Pushed |

**Test suite: 60 → 67 passing (1 skipped, Postgres-only trigram test), all green on your machine.**

## 4. Known-but-not-fixed: lower-priority pharmacy hardening gaps

Flagged, not touched — these are real but lower severity, and involve clinical-judgment tradeoffs worth a team conversation rather than a unilateral change:

- **Allergy matching is a raw substring check.** A patient allergy recorded as "penicillin" won't flag against a prescribed drug whose keyword is "amoxicillin" unless someone explicitly seeded that cross-reference — cross-reactivity within a drug class isn't modeled.
- **Pediatric dose checking depends on the free-text `dose` field literally containing a number + "mg".** `"0.5g"`, `"1 tablet"`, or a blank dose silently skips the check.
- **Pregnancy contraindication only looks at the *latest* vitals record.** If a later routine vitals entry doesn't ask about pregnancy and the field resets toward unknown, an earlier confirmed pregnancy stops being checked.

**Recommendation:** these are worth a short huddle before demo day, not urgent fixes. If judges ask "what would you harden next," this list is a good, honest answer.

---

## 5. Phase-2 Planning — 1 week remaining

The team already speced a priority queue in `docs/phase-2/README.md` (P0–P3). Below is that plan filtered through: (a) actual effort vs. 1 week, (b) the judging weights in `AGENTS.md` §10, (c) what's already partially speced (`emergency-triage` and `inpatient-ward-management` both have a `01_FEATURE_SPEC.md` already — ~60-75 lines each, no build plan yet).

### Judging weights, for reference
Clinical Relevance 20% · Patient Safety 20% · Innovation 15% · Technical Design 15% · Malawi Context Fit 15% · Sustainability 15%

### Reality check on scope
Phase 1 (everything done so far) took the bulk of your ~16 engineering days and multiple contributors. **You will not finish the full P0–P3 list in a week.** Trying to will produce shallow, buggy modules that hurt Patient Safety and Technical Design scores more than an honestly-scoped Phase 1 with a clear "not yet built, here's why" helps. Pick 2, maybe 3, real features and make them as solid as Phase 1 — that's a stronger demo than 6 half-built ones.

### Recommended priority for this week

| Priority | Feature | Why this, why now | Rough effort | Judging payoff |
|---|---|---|---|---|
| **1** | **Emergency & Triage** (§8.1.5) | Spec already started. Small, self-contained: rapid registration + triage category + priority queue. Directly extends `patients`/`vitals`, doesn't need a new heavy domain model. High patient-safety story ("who gets seen first") that's easy to demo live. | 1.5–2 days | Clinical Relevance, Patient Safety |
| **2** | **Inventory / Stock (minimal)** (§8.1.14) | Not full stock management — just a `StockLevel` per `Drug`/`LabTest` with a low-stock flag surfaced on the pharmacy/lab dashboards. Cheap to build (no new complex workflow), and it closes a real gap: right now the system can prescribe a drug regardless of whether it exists on the shelf, which undercuts the "Patient Safety" story you already have. | 1 day | Patient Safety, Malawi Context Fit |
| **3** | **Dialysis & CKD (stub-level)** (§8.1.12) | AGENTS.md explicitly calls this a stretch goal and the Innovation row in §10 names it by name. A deliberately minimal model (dialysis session log FK'd to Patient, linked to existing vitals/labs) gets you the "Innovation" bonus point honestly, without pretending to build a real dialysis unit workflow. | 0.5–1 day | Innovation |
| **Cut for now** | Inpatient/Ward management (§8.1.4) | Already speced (P0 in the team's own doc) but genuinely heavy: admission workflow, bed/ward model, transfer/discharge state machine, a new patient-status concept that touches the dashboard and several existing modules. This is a multi-day feature on its own — starting it and leaving it half-built the week before judging is worse than not starting it. | — | — |
| **Cut for now** | Appointment/Queue (§8.1.2), Nursing docs (§8.1.6), CPOE (§8.1.9), full appointment/SMS, Maternal/Child Health, Theatre, full PACS, Research/Teaching | All reasonable Phase-3 candidates. None earn enough judging weight per day of remaining effort to beat polishing what exists. | — | — |

### Days 4–7: not new features — demo readiness
This matters more than people usually budget for it, and nothing above it is worth trading against:

- **Deploy for real**, once: Render + Neon + Upstash, per AGENTS.md §2. Confirm the cold-start ping-5-minutes-before-demo behavior actually works, don't discover it live.
- **Run the full local Docker Compose fallback once**, unplugged from the internet, exactly as you'd demo the "no ISP" story for Malawi Context Fit.
- **Rehearse the safety-block demo** — this session's pharmacy fix gives you a genuinely good live moment ("watch it refuse to let me override a documented allergy, then watch the safe alternative"). That's a stronger 90-second demo beat than a feature list.
- **A judge will click things you didn't plan for.** Budget half a day for exploratory testing across roles (log in as each of the 8 groups, hit the nav, confirm nothing 500s).
- Update `docs/COMPLETED_FEATURES.md` as the single source of truth as you go — that's the doc-drift lesson from this session; don't let it happen again in week 2.

### If you only do one thing from this list
Emergency & Triage. It's the best effort-to-judging-weight ratio, it's already partially speced, and "who gets seen first when three patients are severe" is exactly the kind of scene that lands with judges evaluating Clinical Relevance and Patient Safety together.

---

## 6. Files changed this session (all pushed to `main`)

```
config/settings.py
accounts/tests.py                      (new)
README.md
CHANGES_SUMMARY.md
pharmacy/safety.py
pharmacy/services.py
pharmacy/views.py
pharmacy/tests.py
templates/pharmacy/prescribe.html
core/management/commands/seed_demo.py
```
