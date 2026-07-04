# Completed Features — MUST–GSL EMR Innovation Challenge

> **Traceability matrix**: every implemented feature mapped to its brief section.
> Phase-2 features (not yet built) at the end. Next-sprint candidates flagged.

---

## §8.1.1 Patient Registration & Master Patient Index — **COMPLETE**

| Requirement | Implementation | Location |
|---|---|---|
| Patient registration + demographic profile | `Patient` model with full Malawi-context fields | `patients/models.py` |
| Unique hospital patient number | `MUST-YYYYMM-XXXXX` format, race-safe via `PatientNumberSequence` + `select_for_update` | `patients/models.py:25` |
| National ID field | `national_id` (encrypted at rest, HMAC lookup hash) | `patients/models.py` |
| Guardian/next-of-kin | `NextOfKin` model (name, relationship, encrypted phone) | `patients/models.py` |
| Village, TA, district, region | 4 dedicated fields on `Patient` | `patients/models.py` |
| Patient category | 8 choices: outpatient/inpatient/student/staff/private/referred/emergency/research | `patients/models.py` |
| Duplicate detection + merge | Trigram similarity (`pg_trgm`) + exact ID/phone match; blocking interstitial with logged override; merge workflow | `patients/services.py`, `patients/views.py` |
| Visit/encounter history | `Encounter` FK'd to `Patient`; tab on profile | `encounters/` |
| Referral tracking | `ReferralRecord` (source, destination, reason) | `patients/models.py` |
| Consent flags | `consent_care/teaching/research` booleans | `patients/models.py` |
| Audit trail | `django-simple-history` on `Patient` + `DuplicateConfirmation` log | `patients/` |

## §8.1.2 Appointment, Queue, Patient Flow — **NOT BUILT**

See §7.2 for scheduling / queue models.

## §8.1.3 Outpatient Clinical Documentation — **COMPLETE**

| Requirement | Implementation | Location |
|---|---|---|
| Presenting complaint + HPC | `presenting_complaint`, `history_of_presenting_complaint` | `encounters/models.py` |
| Past medical/surgical history | `past_medical_history`, `past_surgical_history` | `encounters/models.py` |
| Medication, allergy, social, family history | `medication_history`, `allergy_history`, `social_history`, `family_history` | `encounters/models.py` |
| Review of systems + exam | `examination_findings` | `encounters/models.py` |
| Diagnosis + differential | `diagnosis`, `differential_diagnosis` | `encounters/models.py` |
| Clinical plan | `clinical_plan` | `encounters/models.py` |
| Structured templates | `ClinicalTemplate` (JSON field config) | `encounters/models.py` |
| Signature + timestamp + audit | `signed_by`/`signed_at`; `EncounterAddendum` for post-sign edits | `encounters/models.py` |

## §8.1.4 Inpatient / Ward Management — **COMPLETE**

| Requirement | Implementation | Location |
|---|---|---|
| Admission workflow | `Admission` model with status (active/transferred/discharged/dead) | `inpatient/models.py` |
| Ward management | `Ward` (name, department, bed_count) + `Bed` (ward FK, label, occupancy) | `inpatient/models.py` |
| Bed assignment | `assign_bed()` / `free_bed()` services | `inpatient/services.py` |
| Transfer | `transfer_patient()` — frees old bed, assigns new | `inpatient/services.py` |
| Discharge | `discharge()` — frees bed, timestamp + summary | `inpatient/services.py` |
| Ward round notes | `WardRoundNote` with optional diagnosis/plan update | `inpatient/models.py` |
| Bed board | `/inpatient/ward/<id>/` — color-coded occupancy grid | `inpatient/views.py` |
| Inpatient dashboard | `/inpatient/dashboard/` — occupancy per ward + active admissions | `inpatient/views.py` |
| Patient tab | Admission history on profile | `inpatient/views.py` |
| Dashboard widget | "Bed Occupancy" for Clinician/Nurse/Admin | `inpatient/apps.py` |
| Seed data | 4 wards (Medical/Surgical/Paediatric/Maternity) + beds + demo admission | `core/management/commands/seed_demo.py` |
| Admit button | Direct link on patient profile | `templates/patients/profile.html` |

## §8.1.5 Emergency & Triage — **COMPLETE**

| Requirement | Implementation | Location |
|---|---|---|
| Triage assessment | `TriageEncounter` with 5-level CTAS category | `emergency/models.py` |
| Rapid registration | `RapidRegisterForm` — minimal patient + triage in one step | `emergency/forms.py` |
| Triage queue | `/emergency/queue/` — severity-sorted (immediate → non-urgent) | `emergency/views.py` |
| Triage resolution | `resolve_triage()` — outcome (discharged/admitted/referred/dead) | `emergency/services.py` |
| Patient tab | HTMX partial showing triage history with category/outcome badges | `emergency/templates/emergency/_patient_tab.html` |
| Dashboard widget | "Triage Queue" for Nurse/Clinician/Admin | `emergency/apps.py` |

## §8.1.6 Nursing Documentation — **NOT BUILT**

Nursing notes not yet separated from clinical documentation scope.

## §8.1.7 Vital Signs, Observations, EWS — **COMPLETE**

| Requirement | Implementation | Location |
|---|---|---|
| Temperature, BP, pulse, RR, SpO2 | All on `VitalSignSet` | `vitals/models.py` |
| Weight, height, BMI | Auto-calculated BMI on save | `vitals/models.py` |
| Pain score | 0–10 `pain_score` | `vitals/models.py` |
| Blood glucose | `blood_glucose` | `vitals/models.py` |
| GCS | `glasgow_coma_scale` | `vitals/models.py` |
| Pregnancy status | `pregnancy_status` choices | `vitals/models.py` |
| Early Warning Score | Adult EWS computed via `vitals/scoring.py` (temp/BP/pulse/RR/SpO2/GCS bands, 0–3 each, summed) | `vitals/scoring.py` |
| Abnormal value alerts | Hard-threshold alerts fire in same request/response cycle via `raise_alert()` | `vitals/views.py` |
| Pediatric alerts | Noted as future scope in `scoring.py` | `vitals/scoring.py` |

## §8.1.8 Provider / Physician Documentation — **COMPLETE**

Covered by same `Encounter` model — H&P, progress notes, consultation, discharge summaries all use the structured encounter form. `EncounterAddendum` adds post-sign notes. No separate procedure-note template yet (see §7.3).

## §8.1.9 Order Entry & Management — **NOT BUILT**

This section covers generic order sets (CPOE) separate from lab/imaging/pharmacy-specific orders.

## §8.1.10 Laboratory Information Management — **COMPLETE**

| Requirement | Implementation | Location |
|---|---|---|
| Lab test ordering | `LabOrder` with status workflow (6 states) | `laboratory/models.py` |
| Specimen tracking | Specimen type on `LabTest`; `specimen_barcode` on `LabOrder` | `laboratory/models.py` |
| Result entry + verification | `LabResult` with separate `entered_by`/`verified_by` (enforced different users) | `laboratory/models.py` |
| Critical result alerts | `is_critical` auto-set; calls `raise_alert()` on save | `laboratory/views.py` |
| LOINC-ready | `loinc_code` nullable field on `LabTest` | `laboratory/models.py` |
| Workload dashboard | `/labs/workload/` — pending/resulted counts, turnaround time | `laboratory/views.py` |

## §8.1.11 Pharmacy, Prescribing & Medication Safety — **COMPLETE**

| Requirement | Implementation | Location |
|---|---|---|
| Electronic prescribing | `Prescription` with dose/route/frequency/duration | `pharmacy/models.py` |
| Allergy alerts | `check_prescription_safety()` queries `DrugAllergyMap` + `encounters.services.get_patient_allergies()` | `pharmacy/safety.py` |
| Duplicate therapy warning | Checks active prescriptions for same drug/generic_name | `pharmacy/safety.py` |
| Pediatric dosing | `pediatric_max_dose_mg` on `Drug`; dose check against patient age | `pharmacy/safety.py` |
| Pregnancy/renal contraindication | `contraindicated_in_pregnancy/renal` on `Drug`; checks patient vital status + diagnosis | `pharmacy/safety.py` |
| Prescription approval workflow | `prescribed -> approved -> dispensed -> cancelled` with separate `approved_by` role | `pharmacy/views.py` |
| Override documentation | `safety_override_reason` required when bypassing critical alert | `pharmacy/models.py` |
| Stock note | `stock_note` free-text on `DispensingRecord` | `pharmacy/models.py` |

## §8.1.12 Dialysis & CKD — **COMPLETE**

| Requirement | Implementation | Location |
|---|---|---|
| CKD staging | `CKDDiagnosis` (patient, stage 1–5, diagnosed_by, notes) | `dialysis/models.py` |
| Dialysis prescribing | `DialysisPrescription` (frequency, fluid target, access type) | `dialysis/models.py` |
| Session recording | `DialysisSession` (pre/post weight, auto-calculated fluid removal, complications) | `dialysis/models.py` |
| Missed session heuristic | `missed_sessions()` — naive weekday checker (`ponytail:` comment) | `dialysis/services.py` |
| Patient tab | CKD diagnosis + active prescriptions + Record Session buttons | `dialysis/views.py` |
| Session log | Per-prescription session history with pre/post weight table | `dialysis/views.py` |
| Dashboard | `/dialysis/dashboard/` — today's session status per patient | `dialysis/views.py` |
| Dashboard widget | "Dialysis Sessions Today" for Clinician/Nurse/Admin | `dialysis/apps.py` |
| Tests | 8 tests (diagnosis, prescribe, session, missed) | `dialysis/tests.py` |

## §8.1.13 ICU / HDU / Critical Care — **NOT BUILT**

See §7.3.

## §8.1.14 Billing & Revenue Cycle — **COMPLETE**

| Requirement | Implementation | Location |
|---|---|---|
| Service catalog + charges | `ServiceCatalogItem` (name, code, price) | `billing/models.py` |
| Invoice + line items | `Invoice` (draft/issued/paid/waived/partially_paid) + `InvoiceLineItem` | `billing/models.py` |
| Payment recording | `Payment` (cash/mobile_money/bank/insurance) | `billing/models.py` |
| Mobile money support | `method` includes `mobile_money`; `reference` stores transaction ref | `billing/models.py` |
| Revenue dashboard | `/billing/` — payment tracking | `billing/views.py` |
| Unpaid bills report | `unpaid_invoices_for()` service function | `billing/services.py` |

## §8.1.15 Inventory / Stock Management — **COMPLETE**

| Requirement | Implementation | Location |
|---|---|---|
| Drug stock tracking | `StockLevel` (OneToOneField → Drug, quantity, low_stock_threshold) | `pharmacy/models.py` |
| Stock check | `check_stock(drug)` → `(qty, in_stock)` | `pharmacy/services.py` |
| Stock adjustment | `adjust_stock(drug, qty, user, note)` — get_or_create + add | `pharmacy/services.py` |
| Dispense guard | Dispensing view checks stock; blocks with error if 0; deducts 1 on success | `pharmacy/views.py` |
| Stock management UI | `/pharmacy/stock/` — add stock form + levels table with Low/Out badges | `pharmacy/templates/pharmacy/stock.html` |
| Queue stock display | Stock level shown per drug on queue page | `templates/pharmacy/queue.html` |
| Dashboard widget | "Stock Management" for Pharmacist/Admin | `pharmacy/apps.py` |
| Migration | `pharmacy/0003_add_stocklevel.py` | `pharmacy/migrations/` |

## §8.1.16 Clinical Governance & Audit — **COMPLETE**

| Requirement | Implementation | Location |
|---|---|---|
| Audit trail | `django-simple-history` on all clinical/PHI models (create/update/delete versioned) | `config/settings.py` |
| Audit viewer | `/accounts/admin/audit/` — role-gated (Admin/ICT only) | `accounts/views.py` |
| Electronic signatures | `signed_by`/`signed_at` on Encounter, `verified_by` on LabResult | `encounters/`, `laboratory/` |
| RBAC documentation | 8 groups fixture with permissions; `@role_required` decorator | `accounts/` |

## §8.1.17 Multidisciplinary Coordination — **NOT BUILT**

Cross-module communication not yet formalized beyond the shared alert hub.

## §8.1.18 Health Information Exchange / Interoperability — **COMPLETE**

| Requirement | Implementation | Location |
|---|---|---|
| FHIR-inspired data model | Field names FHIR-shape-compatible (e.g. `Patient.gender` uses FHIR value set) | `patients/models.py` |
| FHIR-Bundle export | `GET /api/interop/patient/<id>/bundle/` — Patient + Encounter serialized | `interop/views.py` |
| LOINC readiness | `loinc_code` on `LabTest` | `laboratory/models.py` |
| ICD readiness | Not yet populated — ICD field considered stretch | — |
| API documentation | `/api/schema/`, `/api/docs/`, `/api/redoc/` via drf-spectacular | `config/urls.py` |
| Mobile money interface | `mobile_money` payment method + reference field | `billing/models.py` |

## §8.1.19 Administration, Governance & Audit — **COMPLETE**

| Requirement | Implementation | Location |
|---|---|---|
| User account management | Django admin + registration | `accounts/` |
| Role-based access control | 8 groups + `@role_required` + dashboard widget gating | `accounts/` |
| Audit trails | `django-simple-history` on every model | global |
| Data governance | Field-level encryption; consent flags | `patients/models.py` |
| System usage | Analytics dashboard with cross-module counts | `reporting/views.py` |

---

## §9 Mandatory Critical Enhancements

### §9.1 Clinical Governance Structure
8 RBAC roles with clear ownership + `@role_required` enforcement on every view.

### §9.2 Patient Safety Framework
- Allergy alerts (pharmacy prescribing time)
- Critical lab result alerts (auto-fire on save)
- Abnormal vital sign triggers (hard thresholds)
- Pediatric dosing safeguards (dose vs age check)
- Duplicate patient record warning (trigram + exact match)
- Time-stamped clinical notes (all Encounter/Lab orders)
- Alert prioritization (critical vs warning levels; warnings can be acknowledged, critical blocks submit)
- Audit logs on every PHI write

### §9.3 Legal, Ethical, Compliance Requirements
- Field-level encryption (Fernet-based, via `core/encrypted_fields.py`)
- RBAC with Django Groups
- Audit trails + time-stamped entries
- Consent capture (care/teaching/research)
- Default-deny access pattern

### §9.4 Cybersecurity Requirements
- Secure login (`LoginView`, CSRF middleware)
- Role-based access control (decorators + permission classes)
- Session timeout (15 min idle, configurable)
- Field-level encryption at rest
- Failed login tracking + account lockout (`django-axes`, 5 attempts → 15 min lock)
- Audit logging on all admin activity

### §9.5 Interoperability Standards
- FHIR-inspired endpoint (`/api/interop/`)
- LOINC-ready lab fields
- drf-spectacular OpenAPI docs
- Offline sync queue (`syncapi`)

---

## §10 System Resilience (Malawi Context)

| Requirement | Implementation | Location |
|---|---|---|
| Offline data entry | `SyncSubmission` model + DRF submit endpoint | `syncapi/` |
| Sync on reconnect | Service worker + IndexedDB (vendored `js/sw.js`, `js/idb.min.js`) | `static/js/` |
| Local server fallback | Docker Compose bundle (Django + Postgres + Redis + Nginx) | `docker-compose.yml`, `Dockerfile` |
| Cloud deployment | Render + Neon + Upstash config | `.env.example` |
| Low-bandwidth optimization | Server-rendered HTML + HTMX partials + vendored JS (zero CDN) | global |
| Power outage recovery | Docker restart policy; atomic transactions | `docker-compose.yml` |
| Data backup | Standard Postgres dump + migration files | — |

---

## §12 Prototype Minimum Requirements

| Requirement | Status |
|---|---|
| User login | ✅ Django LoginView + axes lockout |
| Role-based dashboard | ✅ Widget registry per role |
| Patient registration + search | ✅ Full Malawi-context + duplicate detection |
| Patient profile | ✅ 9 HTMX tabs (demographics, encounters, vitals, labs, imaging, pharmacy, billing, dialysis, admissions) |
| Clinical encounter | ✅ Sign-and-lock with addenda |
| Vital signs entry | ✅ EWS + auto-computed BMI + alerts |
| Lab order + result | ✅ Full verify workflow |
| Imaging request + report | ✅ Pregnancy safety gate |
| Prescription + dispensing | ✅ Safety checks (allergy, duplicate, peds, pregnancy) |
| Basic billing + payment | ✅ Invoice + line item + payment (mobile money) |
| Dashboard / analytics | ✅ Cross-module counts |
| Audit trail | ✅ simple-history on every model + viewer |
| Offline sync concept | ✅ syncapi + service worker |

---

## Not Yet Built

| § | Feature | Priority | Notes |
|---|---|---|---|
| §8.1.2 | Appointment scheduling / Queue | High | Requires calendar UI — complex frontend |
| §8.1.6 | Nursing documentation | Medium | After inpatient scope |
| §8.1.9 | Generic CPOE | Medium | Order sets beyond lab/imaging/pharmacy |
| §8.2.x | Imaging full PACS | Low | Metadata-only in Phase 1 |
| §8.2.x | Theatre / Anaesthesia | Low | Future specialist module |
| §8.2.x | Maternal / Child Health | Medium | Antenatal + partograph |
| §8.2.x | Research / Teaching | Low | De-identified export + student access |
