# Engineer E — Module Spec: Billing, Dialysis (stretch), Reporting/Alerts, Interoperability & Offline Sync

**Django apps owned:** `billing`, `dialysis`, `reporting`, `interop`, `syncapi`.

This is the broadest module — it's also the one with the most true MVP-vs-stretch flexibility. **Build in this order: `reporting` (alert hub, needed by everyone) → `billing` (MVP) → `syncapi` (MVP-adjacent, offline story) → `interop` (bonus) → `dialysis` (bonus).** Do not start `dialysis` or `interop` until `billing` and `syncapi` acceptance criteria pass — they're what the judging rubric actually requires; the rest is what makes you stand out once the base is solid.

**Depends on:** `patients.Patient` (Engineer A), plus read access to encounters/labs/pharmacy data for dashboards — all via each app's `services.py`, never direct model imports.

**Brief traceability:** §8.1.14 (Billing), §8.1.12 (Dialysis — future module, explicitly named repeatedly across the brief as a phase-1-adjacent priority), §9.2/§10 (alerts, resilience), §7.5/§8.1.18/§9.5 (interoperability), §12 MVP ("basic billing and payment status", "dashboard or analytics page", "backup, offline synchronization, or local server fallback concept").

## 1. `reporting` app (build first — everyone else's alerts depend on it)

```
AlertEvent
  - patient      FK(patients.Patient)
  - source          CharField (vitals/lab/imaging/pharmacy/system)
  - severity           CharField choices: info/warning/critical
  - message               TextField
  - raised_at
  - acknowledged_by  FK(User, null=True)
  - acknowledged_at  DateTimeField null=True
```

Public interface (`reporting/services.py`) — this is the single shared entry point every other engineer calls:
```python
def raise_alert(patient, source: str, severity: str, message: str) -> AlertEvent
def unacknowledged_alerts(limit=20) -> QuerySet[AlertEvent]
def acknowledge(alert, user) -> AlertEvent
```

Also owns the **dashboard/analytics page** (§12): a single `/dashboard/analytics/` view aggregating counts from each module via their `services.py` (patients registered today, open encounters, pending labs, pending prescriptions, unpaid bills, unacknowledged alerts) — this is the "dashboard or analytics page" MVP line item and the natural home for it since it's cross-cutting by nature.

**Publish `raise_alert()`'s signature to the whole team by end of Day 2** — Engineers B, C, D are all blocked on it for their patient-safety features.

## 2. `billing` app (MVP)

```
ServiceCatalogItem  # seed: consultation, lab test (generic), imaging (generic), pharmacy dispensing fee, admission/bed-day, procedure
  - name, code, price_mwk  DecimalField

Invoice
  - patient      FK(patients.Patient)
  - created_by      FK(User)
  - status            CharField choices: draft/issued/paid/waived/partially_paid
  - payer_type          CharField choices: self_pay/insurance/institutional/waiver
  - created_at (history via django-simple-history)

InvoiceLineItem
  - invoice  FK(Invoice, related_name="line_items")
  - service_item  FK(ServiceCatalogItem)
  - quantity        IntegerField default=1
  - amount_mwk         DecimalField  # snapshot of price at time of billing, don't recompute from catalog later

Payment
  - invoice  FK(Invoice, related_name="payments")
  - amount_mwk
  - method      CharField choices: cash/mobile_money/bank/insurance
  - reference     CharField, blank=True   # "mobile money interfaces" §8.1.18 — MVP stores a reference string, does not integrate a live payment gateway
  - received_by  FK(User)
  - received_at
```

Public interface: `create_invoice`, `add_line_item`, `record_payment`, `outstanding_balance(invoice)`, `unpaid_invoices_for(patient)`.

## 3. `syncapi` app (MVP-adjacent — the offline story)

Implements the pattern defined in root `AGENTS.md` §6.

```
SyncSubmission
  - client_uuid   CharField unique  # generated client-side at queue time, prevents duplicate replay
  - form_type       CharField (which offline-capable form this is: vitals_entry, encounter_note, etc.)
  - payload_json      JSONField
  - patient            FK(patients.Patient, null=True)  # nullable: registration itself can be queued offline
  - submitted_by         FK(User)
  - status                  CharField choices: pending/applied/conflict/rejected
  - received_at
  - applied_at
  - conflict_note            TextField, blank=True

SyncConflict
  - submission  OneToOneField(SyncSubmission)
  - conflicting_record_description  TextField
  - resolved_by  FK(User, null=True)
  - resolved_at
```

`POST /api/sync/submit/` (DRF): accepts a queued submission with `client_uuid`. If `client_uuid` already processed, return the prior result idempotently (no duplicate application). Otherwise, dispatch to the correct app's `services.py` create function based on `form_type`, wrapped in a transaction. If a conflict is detected (e.g. the encounter this vitals reading belongs to was closed/signed in the meantime), create a `SyncConflict` instead of silently applying — per root `AGENTS.md` §6, this is a safety requirement, not optional polish.

`GET /api/sync/status/` — lets the frontend service worker check which queued items have been applied.

## 4. `interop` app (bonus)

One read-only endpoint: `GET /api/interop/patient/<id>/bundle/` returning a FHIR-Bundle-shaped JSON document (Patient resource + recent Encounter/Observation/MedicationRequest-shaped entries) built from existing models via serializers — **read-only, no write-back, no claim of full FHIR conformance**. Document clearly in the System Design Document that this is a "FHIR-inspired export for interoperability readiness," matching the brief's own phrasing, not a certified FHIR API.

## 5. `dialysis` app (bonus — only after MVP is solid)

```
CKDDiagnosis — patient FK, stage (1-5), diagnosed_by, diagnosed_at
DialysisPrescription — patient FK, frequency_per_week, target_fluid_removal_l, vascular_access_type
DialysisSession — prescription FK, session_date, pre_weight_kg, post_weight_kg,
                    fluid_removed_l, complications (TextField, blank=True), conducted_by FK(User)
```
Reuses `ClinicalTemplate` pattern from Engineer B where useful. Public interface + a simple "missed session" flag (session expected on schedule but not recorded within a grace window) computed in a `dialysis/services.py` function, surfaced as a dashboard widget. This single module, if you get to it, earns real Innovation (15%) points because almost no competing team will have built a working chronic-care longitudinal module — but it is explicitly last priority, don't start it with MVP items incomplete.

## 6. Acceptance criteria

- [ ] `raise_alert()` is live and callable by end of Day 2; unacknowledged alerts show on the analytics dashboard in real time (next page load, not polling-delayed).
- [ ] An invoice can be created with multiple line items, a payment recorded against it, and outstanding balance computed correctly.
- [ ] Analytics dashboard shows real, correct counts pulled from every other module's seed data.
- [ ] A form submitted via `POST /api/sync/submit/` with a duplicate `client_uuid` does not create a duplicate record (idempotency test).
- [ ] A conflicting queued submission produces a `SyncConflict`, not a silent overwrite.
- [ ] (Bonus) `/api/interop/patient/<id>/bundle/` returns valid JSON shaped recognizably like a FHIR Bundle for a seeded patient.
- [ ] (Bonus) Dialysis module supports recording a session and flags a missed one against schedule.
