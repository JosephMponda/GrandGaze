# Specs Review — GrandGaze vs. MUST–GSL EMR Brief v31'05'2026

> **Unbiased, no-sugarcoating system review.** Every claim tested against the brief.
> Similar = matches brief. Different = diverges. Gap = missing entirely.
> Reference PDF is the single source of truth.

---

## §7 Design Principles

### §7.1 Patient Safety First
**Brief:** "Reduce clinical risk, not create additional risk. Accurate documentation, safe prescribing, allergy alerts, abnormal result notifications, clear accountability."

| Aspect | Verdict | Detail |
|---|---|---|
| Allergy alerts | **Similar** | `CriticalSafetyBlock` prevents prescribing known allergens. Keyword substring matching via `DrugAllergyMap`. |
| Abnormal result alerts | **Similar** | Vitals hard thresholds → `AlertEvent`. Lab critical results → `AlertEvent`. Imaging critical findings → `AlertEvent`. Synchronous, same request cycle. |
| Clear accountability | **Similar** | `django-simple-history` on all PHI models. `encounter.signed_by`, `lab_result.verified_by`. |
| Drug-drug interaction | **Gap** | No `DrugInteraction` model exists. §8.1.11 requires interaction warnings. Zero implementation. |
| Alert fatigue reduction | **Similar** | Warning-level alerts acknowledgeable (bypass with override reason). Critical alerts are absolute blocks. |
| Breastfeeding/lactation warning | **Gap** | No `contraindicated_in_breastfeeding` Drug field, no vitals breastfeeding status, no check. |

### §7.2 Simplicity and Usability
**Brief:** "Easy for nurses, clinicians, pharmacists, lab personnel, imaging, billing, administrators, students, ICT staff."

| Aspect | Verdict | Detail |
|---|---|---|
| Role-based simplified UI | **Similar** | Role-gated nav links + role-gated dashboard widgets. |
| HTMX partial swaps | **Different** | Brief doesn't specify rendering approach. Our Django Templates + HTMX + Alpine reduces page loads, good for low-bandwidth. This is a strength. |
| No training materials | **Gap** | No help system, no user manual, no onboarding guide. §19 expects training/adoption materials. |

### §7.3 Malawi Context Fit
**Brief:** "Local clinical workflows, patient ID challenges, village/TA structures, connectivity limitations."

| Aspect | Verdict | Detail |
|---|---|---|
| Village, TA, district, region fields | **Similar** | All 4 fields on Patient model. |
| `age_estimated` flag | **Similar** | Boolean field for unknown DOB (common in Malawi). |
| Patient category (8 choices) | **Similar** | Includes `research participant`, `student`, `staff`, `referred`, `emergency`. |
| Encrypted national_id + phone | **Similar** | Fernet encryption + HMAC-SHA256 blind index for lookup. |
| Offline support | **Similar** | Service worker + IndexedDB + `syncapi` replay. |
| Local server fallback | **Similar** | Docker Compose bundle (Django + Postgres + Redis + Nginx). |
| Mobile money billing field | **Similar** | `mobile_money` payment method + reference field. |
| Low-bandwidth optimization | **Similar** | Server-rendered HTML, vendored JS (zero CDN), minimal JS footprint. |
| Biometric-ready design | **Gap** | No `biometric_hash`, `fingerprint_template`, or any biometric field on Patient. §8.1.1 requires "biometric-ready design." |
| `consent_data_use` flag | **Gap** | Only `consent_care`, `consent_teaching`, `consent_research` exist. §8.1.1 specifies "data use." |

### §7.4 Scalability
**Brief:** "Modular, phased growth from outpatient clinic to teaching hospital."

| Aspect | Verdict | Detail |
|---|---|---|
| Django app separation | **Similar** | 11 modular apps with bounded contexts. |
| Cross-app via services.py only | **Similar** | Internal service functions in each app's `services.py`. Violations exist (emergency imports `_generate_patient_number`). |
| No async queue for scalability | **Different** | Brief doesn't mandate background jobs. Our Celery is "week-2 if capacity allows" — acceptable for MVP. |

### §7.5 Interoperability
**Brief:** "DHIS2, HL7 FHIR, DICOM, LOINC, MaHIS, HIE API, 'One patient, one record.'"

| Aspect | Verdict | Detail |
|---|---|---|
| FHIR-inspired export | **Similar** | `/api/interop/patient/<id>/bundle/` returns Patient + Encounter in FHIR-Bundle shape. No conformance claim. |
| LOINC-ready lab tests | **Different** | `LOINC_CODE` field exists but only 2/7 seeded tests have codes. REFERENCE_ALIGNMENT.md claims 5/7 codes that are NOT in the actual seed data. Docs ≠ code. |
| ICD-11 diagnosis coding readiness | **Gap** | No ICD code field on Encounter.diagnosis. Free-text only. |
| DICOM-ready imaging | **Different** | Metadata-only (`image_reference` free-text field). Per AGENTS.md §8, this is intentional scope-cap. "Image-link concept" exists. |
| DHIS2/MaHIS integration | **Gap** | No DHIS2 export, no MaHIS linkage, no HIE API integration. |

### §7.6 Security and Privacy
**Brief:** "RBAC, authentication, encryption, logging, audit trails, data governance."

| Aspect | Verdict | Detail |
|---|---|---|
| RBAC via Groups + decorators | **Similar** | 8 groups, `@role_required` decorator, navigation gating. |
| Field-level encryption | **Similar** | Fernet-based `EncryptedCharField`, HMAC blind index. |
| Audit trails (django-simple-history) | **Similar** | On every PHI model. |
| MFA concept | **Gap** | No multi-factor authentication anywhere. §9.4 requires "multi-factor authentication concept." |
| Session timeout (15 min) | **Similar** | SESSION_COOKIE_AGE = 900 seconds. |
| Idle timer warning (13 min) | **Gap** | AGENTS.md §7 promises Alpine idle-timer. Not implemented. |
| Password policy (min 10 chars) | **Similar** | 4 Django validators including min length 10. |
| django-axes lockout (5/15min) | **Similar** | 5 failed → 15 min cooldown per username+IP. |
| AlertEvent audit trail | **Gap** | `AlertEvent` is NOT registered with `django-simple-history`. Alert acknowledgements are invisible in audit trail. |

### §7.7 Sustainability
**Brief:** "Maintenance, upgrades, training, local ownership, long-term support."

| Aspect | Verdict | Detail |
|---|---|---|
| Free-tier-first hosting | **Similar** | Render + Neon + Upstash. |
| Open-source stack | **Similar** | Django, PostgreSQL, Python — maintainable by local devs. |
| Docker Compose deployment | **Similar** | Single-laptop bundle. |
| No dedicated sustainability plan | **Gap** | §19.6 requires a sustainability document. No standalone document exists — only implicit in AGENTS.md. |
| Training/adoption plan | **Gap** | No training strategy documented. §19.6 requires training plan. |

---

## §8 Core Modules

### §8.1.1 Patient Registration & MPI
**Brief:** Registration, unique patient number, National ID, name/sex/DOB/age/phone/address, guardian/NOK, village/TA/district/region, occupation, patient category (8), biometric-ready, duplicate detection + merge, visit history, referral source/destination, consent flags (care/teaching/research/data use).

| Aspect | Verdict | Detail |
|---|---|---|
| Patient number (MUST-YYYYMM-NNNNN) | **Similar** | Race-safe via `select_for_update` + `PatientNumberSequence`. |
| National ID (encrypted + HMAC lookup) | **Similar** | Fernet encryption + HMAC blind index. |
| Name, sex, DOB, age, phone, address | **Similar** | All present. |
| Guardian/next-of-kin | **Different** | `NextOfKin` model exists BUT profile template references `patient.guardian_name` and `patient.guardian_phone` — attributes that DO NOT EXIST on Patient. Template bug. |
| Village, TA, district, region | **Similar** | All 4 present. |
| Occupation/school | **Similar** | `occupation_or_school` single field. |
| Patient category (8 choices) | **Similar** | All 8 from brief exactly. |
| Biometric-ready | **Gap** | No biometric fields. |
| Duplicate detection | **Similar** | Trigram similarity (`pg_trgm`) + exact HD match via HMAC hash. Blocking interstitial. |
| Merge workflow | **Different** | `PatientMergeRecord` audit model exists but NO merge logic (no data reassignment, no FK migration, no deactivation). Audit shell only. |
| Visit history | **Similar** | Via `encounters` app FK. |
| Referral source/destination | **Different** | `ReferralRecord` model exists but is admin-only. No UI, no workflow, no status tracking. |
| Consent: care, teaching, research | **Similar** | All 3 present. |
| Consent: data use | **Gap** | Missing. |
| Age computation property | **Gap** | No `age` property on Patient model. Template references `patient.age_is_estimated` — model field is `age_estimated`. Template bug. |
| Patient edit/update view | **Gap** | No way to update demographics after registration. |

### §8.1.2 Appointment, Queue, Patient Flow
**Brief:** Appointment booking, clinic scheduling, provider scheduling, check-in/check-out, queue management, triage prioritization, emergency flagging, referral, missed appointment tracking, follow-up generation, SMS reminders.

| Aspect | Verdict | Detail |
|---|---|---|
| All requirements | **Gap** | Not implemented. The docs/phase-2/appointment-scheduling/ directory is EMPTY. This is the highest-priority missing module. |

### §8.1.3 Outpatient Clinical Documentation
**Brief:** Presenting complaint + HPC, PMH/PSH, medication/allergy/social/family history, ROS + exam, diagnosis + differential, clinical plan, structured templates, signature + timestamp + audit.

| Aspect | Verdict | Detail |
|---|---|---|
| Presenting complaint + HPC | **Similar** | Required field (only one). |
| PMH, PSH, med history, allergy history, social, family | **Similar** | All free-text TextFields. |
| ROS + exam | **Different** | No dedicated ROS field. Clinicians must put it in `examination_findings`. |
| Diagnosis + differential | **Similar** | `diagnosis` (CharField 255, single string) + `differential_diagnosis` (free-text). |
| Structured clinical template | **Different** | `ClinicalTemplate` model exists with JSONField but NO view/flow/form uses it. Declared but dead code. |
| Sign + timestamp + audit | **Similar** | `signed_by`, `signed_at`, `status=closed`, `EncounterAddendum` for post-sign. |
| Encounter type diversity | **Gap** | Only 3 types: outpatient/emergency/follow_up. No inpatient, admission, discharge, consultation, procedure note types. |

### §8.1.4 Inpatient / Ward Management
**Brief:** Admission request + diagnosis, ward/bed allocation, transfers, ward round notes, nursing care plans, fluid balance + I/O monitoring, MAR, observation charts, procedure notes, discharge planning + summary, death documentation, inpatient billing linkage, bed occupancy dashboard.

| Aspect | Verdict | Detail |
|---|---|---|
| Admission + diagnosis | **Similar** | `Admission` model with `admission_diagnosis`, status (active/transferred/discharged/dead). |
| Ward + bed allocation | **Similar** | `Ward` + `Bed` models. `assign_bed()`, `free_bed()`, transfer service. |
| Transfers | **Similar** | `transfer_patient()` — frees old bed, assigns new. |
| Ward round notes | **Similar** | `WardRoundNote` with `diagnosis_update`, `plan_update`. BUT missing `signed_by`/`signed_at` from feature spec. |
| Nursing care plans | **Gap** | Not implemented. |
| Fluid balance / I/O monitoring | **Gap** | Not implemented. |
| MAR (Medication Administration Record) | **Gap** | Not implemented. |
| Observation charts | **Gap** | No vitals integration in inpatient context. |
| Procedure notes | **Gap** | Not implemented. |
| Discharge summary | **Partial** | `discharge_summary` + `discharge_disposition` exist. No structured checklist or medication reconciliation. |
| Death documentation | **Different** | `DEAD` status exists but `discharge()` service always sets `DISCHARGED`, never `DEAD`. Bug. |
| Inpatient billing linkage | **Gap** | No billing integration. Service catalog has "Admission Bed-Day" (BED) at MWK 15,000 but no auto-charging. |
| Bed occupancy dashboard | **Similar** | Color-coded grid per ward + dashboard widget. |

### §8.1.5 Emergency & Triage
**Brief:** Emergency registration, minimal data rapid registration, triage category + presenting condition, vital signs + emergency alerts, resuscitation notes + trauma notes, time-critical event recording, referral to theatre/ICU/imaging/lab/ward, emergency outcome (discharge/admission/referral/death).

| Aspect | Verdict | Detail |
|---|---|---|
| Rapid registration (minimal) | **Similar** | Name + sex + age_estimate + triage + presenting condition in one form+transaction. |
| Triage category (5-level CTAS) | **Similar** | Immediate → Non-urgent, color-coded, severity-sorted queue. |
| Triage queue | **Similar** | Sorted by severity, unresolved only. |
| Emergency outcome (4 options) | **Similar** | discharged/admitted/referred/dead. |
| Vital signs + emergency alerts | **Gap** | No integration with vitals app. No `EmergencyVitalSet` bridge model (despite being in feature spec). `raise_alert()` is never called from emergency. |
| Resuscitation notes | **Gap** | `ResuscitationNote` model from feature spec — not implemented. |
| Time-critical event recording | **Gap** | Not implemented. |
| Structured referral (theatre/ICU/imaging/lab/ward) | **Partial** | Free-text `disposition_note` only. No auto-creation of LabOrder, ImagingRequest, or Admission. |
| Outcome → admission workflow | **Gap** | "Admitted" outcome doesn't auto-create an inpatient `Admission`. |

### §8.1.6 Nursing Documentation
**Brief:** Nursing assessment, problem list, care plans, vital signs monitoring, pain assessment, fall/pressure sore risk, wound care, MAR, nursing handover, escalation, patient education.

| Aspect | Verdict | Detail |
|---|---|---|
| All requirements | **Gap** | Not implemented at all. No nursing-specific module exists. |

### §8.1.7 Vital Signs & Clinical Monitoring
**Brief:** Temp/BP/pulse/RR/SpO2, weight/height/BMI/pain, blood glucose/GCS, EWS, pediatric age-adjusted alerts, pregnancy status, abnormal value alerts + trend charts.

| Aspect | Verdict | Detail |
|---|---|---|
| All standard vitals | **Similar** | All present on `VitalSignSet`. |
| BMI auto-calc | **Similar** | On save from weight/height. |
| Pain score (0-10) | **Similar** | Recorded but not used in EWS or alerting. |
| Blood glucose + GCS | **Similar** | Both present. |
| Pregnancy status | **Similar** | 4 choices (n/a/pregnant/not_pregnant/unknown). |
| EWS (simplified NEWS) | **Similar** | 5-parameter adult scoring (temp/BP/pulse/RR/SpO2), 0-3 per band, summed. 4 risk levels. |
| Pediatric age-adjusted alerts | **Different** | Explicit TODO comment: "future scope." Brief says "pediatric age-adjusted vital sign alerts." Not implemented. |
| Supplemental oxygen score | **Gap** | Frontend Alpine calculator includes it; backend scoring.py does NOT. Mismatch. |
| GCS as consciousness proxy | **Different** | Standard NEWS uses ACVPU. Our implementation uses GCS < 15 → +3 points. |
| Trend charts (visual) | **Gap** | Tabular trend only. No charting library used. |
| Hard threshold alerts | **Similar** | 5 hard thresholds → `raise_alert()`. |

### §8.1.8 Physician/Provider Documentation
**Brief:** H&P, Admission Notes, Progress Notes, Consultation Notes, Procedure Notes, Discharge Summaries, Medication Reconciliation, Clinical Decision-Making.

| Aspect | Verdict | Detail |
|---|---|---|
| H&P | **Partial** | All history elements present but no structured ROS. |
| Admission Notes | **Gap** | No `admission` encounter type. |
| Progress Notes | **Gap** | No dedicated progress note type. |
| Consultation Notes | **Gap** | No consultation type. |
| Procedure Notes | **Gap** | No procedure note model. |
| Discharge Summaries | **Partial** | `discharge_summary` on Admission model — not a standalone encounter type. |
| Medication Reconciliation | **Gap** | No structured reconciliation workflow. |

### §8.1.9 Provider Workflow Integration
**Brief:** Order entry + management, diagnostic result review + acknowledgment, interdisciplinary communication, escalation + critical value notification, care plan updates.

| Aspect | Verdict | Detail |
|---|---|---|
| Order entry from encounter | **Gap** | Encounter detail page has mock/placeholder buttons ("Add Prescription", "Order Labs") — no HTMX hooks, no backend integration. |
| Diagnostic result review | **Gap** | No encounter-level result review view. |
| Interdisciplinary communication | **Gap** | No messaging, task assignment, or referral mechanism. |
| Escalation workflow | **Gap** | Alerts fire (vitals/lab/imaging) but no structured escalation (e.g., "notify senior if EWS > 5"). |

### §8.1.10 Laboratory Information Management
**Brief:** Lab test ordering, specimen tracking + barcode, sample receipt + processing status, result entry + verification + approval, critical result alerts, result history + printable reports, workload dashboard + turnaround time, reagent inventory, quality control, external laboratory linkage, LOINC.

| Aspect | Verdict | Detail |
|---|---|---|
| Lab test ordering (6 states) | **Similar** | 6 states, 5 reachable (CANCELLED has no view). |
| Specimen barcode | **Similar** | Visual CSS barcode rendering. |
| Result entry + separate verification | **Similar** | Service-layer enforcement of different users (no DB-level constraint). |
| Critical result alerts | **Similar** | `raise_alert()` on save if outside range. Tested with boundary values. |
| LOINC codes on tests | **Different** | Field exists but only 2/7 seeded tests have codes. REFERENCE_ALIGNMENT.md claims codes for 5 — docs ≠ code. |
| Workload dashboard | **Similar** | 3 metrics (pending, resulted, avg turnaround). Missing per-test-type, per-user, overdue views. |
| Quality control documentation | **Gap** | No QC models. |
| Reagent inventory | **Gap** | No reagent models. |
| External laboratory linkage | **Gap** | No models. |
| Printable lab reports | **Gap** | No export/print views. |
| ~20 seed tests | **Different** | Only 7 seeded. Module spec says ~20. |

### §8.1.11 Pharmacy, Prescribing, Medication Safety
**Brief:** E-prescribing, drug/ formulation/dose/route/frequency/duration, allergy alerts + duplicate therapy warning, drug interaction warning concept, pediatric dosing safeguards, pregnancy + breastfeeding warning concept, renal dose adjustment warning concept, prescription approval workflow, dispensing + medication administration linkage, medication history, stock availability indicator, controlled medicines tracking concept, pharmacy workload dashboard.

| Aspect | Verdict | Detail |
|---|---|---|
| E-prescribing | **Similar** | Full dose/route/frequency/duration. |
| Allergy alerts | **Similar** | Keyword substring match via `DrugAllergyMap`. Ignores allergy severity (mild = critical block). |
| Duplicate therapy warning | **Similar** | 30-day lookback on same `generic_name`. Warning-level (acknowledgeable). |
| Drug interaction warning | **Gap** | Zero implementation. No model, no check function. This is a HIGH-SEVERITY gap for "Medication Safety" module. |
| Pediatric dosing | **Partial** | mg-only, age < 12, regex `_parse_mg()` only matches "NNN mg". No weight-based, no age-banded, no liquid concentration. Bypassed if DOB missing (common Malawi). |
| Pregnancy warning | **Partial** | Requires latest vitals pregnancy_status==PREGNANT. Uses `contraindicated_in_pregnancy` boolean. Warning-level only. |
| Breastfeeding warning | **Gap** | No lactation check, no Drug field, no vitals field. |
| Renal dose adjustment | **Partial** | Keyword-only check on first 5 encounter diagnoses. No eGFR/Cr data, no dose recommendation. Concept-level only — which the spec says it is. |
| Prescription approval workflow (4 states) | **Similar** | prescribed → approved → dispensed or cancelled. Status transitions not enforced at model level. Cancel has no view/UI. |
| Stock availability indicator | **Similar** | `StockLevel` model, check/adjust services, dispense guard, stock.html UI. |
| Controlled medicines tracking | **Different** | `Drug.is_controlled` field exists but: never set in seed data, no workflow, no UI, no dual-sign-off, no register. Stub only. |
| Pharmacy workload dashboard | **Gap** | `/pharmacy/dashboard/` from module spec doesn't exist. Only queue + stock views. |

### §8.1.12 Dialysis & CKD
**Brief:** CKD diagnosis + staging, dialysis registration + prescription, session record, pre/post weight, fluid removal target, vascular access type, complications, lab monitoring + medication tracking, dialysis schedule + missed session tracking, longitudinal chronic care dashboard.

| Aspect | Verdict | Detail |
|---|---|---|
| CKD staging (1-5 + 3a/3b) | **Similar** | Correct KDIGO-compatible staging (6 stages with 3a/3b split). |
| Dialysis prescription | **Similar** | Frequency, fluid target, access type (5 choices). |
| Session record | **Similar** | Pre/post weight, auto-calculated fluid removal, complications. |
| Missed session tracking | **Similar** | Naive weekday heuristic (acknowledged "ponytail" in code). Functional for demo. |
| Lab monitoring for CKD | **Gap** | No integration with laboratory app. No creatinine/eGFR tracking. |
| Medication tracking for CKD | **Gap** | No pharmacy link. No ESA/iron/phosphate binder tracking. |
| Longitudinal chronic care dashboard | **Partial** | Dashboard shows today's sessions only. No eGFR trends, no lab trends, no weight trends over time. |
| Dialysis adequacy (Kt/V, URR) | **Gap** | No adequacy tracking. |

### §8.1.13 ICU / HDU / Critical Care
**Brief:** ICU admission note, continuous observation, ventilation + oxygen therapy, fluid balance + infusion, inotropes/sedation, critical care procedures, sepsis alert, critical result alerts, nursing care plans, daily ICU review, ICU discharge, mortality/morbidity dashboard.

| Aspect | Verdict | Detail |
|---|---|---|
| All requirements | **Gap** | Not implemented. |

### §8.1.14 Billing & Revenue Cycle
**Brief:** Service-based billing, consultation/lab/imaging/pharmacy/procedure/theatre/admission/bed/consumables charges, invoice + receipt generation, payment status + mobile money reference, insurance/institutional payer, waiver/exemption approval workflow, revenue dashboard + unpaid bills report.

| Aspect | Verdict | Detail |
|---|---|---|
| Service catalog + charges | **Similar** | 9 seed items including bed-day, pharmacy fee. |
| Invoice + line items (snapshot pricing) | **Similar** | Correct snapshot-at-billing pattern. |
| Payment recording (4 methods) | **Similar** | Cash, mobile_money, bank, insurance. |
| Mobile money reference | **Similar** | `reference` CharField on Payment. |
| Revenue dashboard | **Partial** | Count metrics only — no MWK totals, no charts, no aging. |
| Unpaid bills report | **Partial** | Per-patient only (`unpaid_invoices_for`). No system-wide report. |
| Insurance/institutional payer | **Partial** | `payer_type` field exists. No provider model, no policy number, no authorization code. |
| Waiver/exemption workflow | **Gap** | WAIVED status exists but no approval model, no workflow, no UI to set it. |
| Receipt generation | **Gap** | No receipt model, template, or PDF generation. |
| Inpatient billing linkage | **Gap** | No auto-charging for admissions/procedures. |

### §8.1.15 Inventory / Stock
**Brief:** Pharmacy stock, lab reagents, imaging consumables, theatre consumables, ward supplies, stock alerts + expiry tracking, batch tracking, equipment maintenance records, biomedical downtime reporting, clinical-to-inventory consumption linkage.

| Aspect | Verdict | Detail |
|---|---|---|
| Pharmacy drug stock | **Similar** | `StockLevel` per drug, low-stock threshold, adjust/check services. |
| Stock alerts + badges | **Similar** | Low/Out badges on queue, dispense, stock views. |
| Dispense guard (blocks if 0) | **Similar** | Redirect with error if out of stock. |
| Consumables for lab/imaging/theatre/ward | **Gap** | Only pharmacy drug stock. No other department inventory. |
| Expiry tracking | **Gap** | No expiry date on StockLevel. |
| Batch tracking | **Gap** | No batch/lot model. |
| Equipment maintenance | **Gap** | Not implemented. |

### §8.1.16 Clinical Governance & Patient Safety
**Brief:** Documentation compliance standards, authentication + electronic signatures, regulatory/accreditation requirements, audit trail functionality.

| Aspect | Verdict | Detail |
|---|---|---|
| Electronic signatures | **Similar** | `signed_by`/`signed_at` on Encounter, `verified_by` on LabResult. |
| Audit trails | **Partial** | `django-simple-history` on all PHI models. BUT `AlertEvent` itself is NOT historied — alert acknowledgements invisible. |
| Documentation compliance | **Gap** | No compliance-checking views. |
| Regulatory/accreditation views | **Gap** | No regulatory dashboard. |

### §8.1.17 Multidisciplinary Coordination
**Brief:** Nursing-provider communication, pharmacy review integration, allied health documentation, case management + discharge planning collaboration.

| Aspect | Verdict | Detail |
|---|---|---|
| All requirements | **Gap** | Not implemented. |

### §8.1.18 Health Information Exchange / Interoperability
**Brief:** API-ready architecture, FHIR-inspired data exchange, DICOM-ready, LOINC-ready, ICD-10/11 readiness, Ministry reporting linkage, national digital health linkage, lab equipment interfaces, mobile money interfaces, mHealth integration, secure data export/import.

| Aspect | Verdict | Detail |
|---|---|---|
| API-ready (DRF) | **Similar** | DRF + drf-spectacular OpenAPI docs. |
| FHIR-inspired export | **Similar** | Single endpoint: Patient + Encounter bundle. |
| LOINC-ready | **Partial** | Field exists on LabTest. Only 2/7 seeded. |
| ICD-10/11 readiness | **Gap** | No ICD field on diagnosis. |
| DICOM-ready | **Gap** | Metadata placeholder only. No DICOM UID, no tags, no modality worklist. (Intentional scope-cap per AGENTS.md.) |
| Ministry reporting | **Gap** | No DHIS2 export. |
| National HIE integration | **Gap** | No MaHIS linkage. |

### §8.1.19 Administration, Governance, Audit
**Brief:** User account management, RBAC, department configuration, service catalog + facility config, audit trails + access logs, data backup monitoring, system usage reports, change control log, incident reporting, downtime reporting, data governance dashboard.

| Aspect | Verdict | Detail |
|---|---|---|
| User account management | **Similar** | Django admin + `accounts` app. |
| RBAC (8 groups) | **Similar** | `@role_required` decorator. Nav gating uses Profile.role (can diverge from Group membership). |
| Audit trails + access logs | **Partial** | Write-level only via simple-history. No read-access logging. `AlertEvent` not historied. |
| System usage reports | **Partial** | Analytics dashboard with 6 live counts. No trends, no export, no date filtering, no per-module drill-down. |
| Department configuration | **Gap** | No Department model or configuration UI. |
| Service catalog + facility config | **Partial** | ServiceCatalogItem exists. No facility configuration model. |
| Data backup monitoring | **Gap** | No backup status display anywhere. |
| Change control log | **Gap** | Not implemented. |
| Incident reporting | **Gap** | Not implemented. |
| Downtime reporting | **Gap** | Not implemented. |
| Data governance dashboard | **Gap** | Not implemented. |

---

## §9 Mandatory Critical System Enhancements

### §9.1 Clinical Governance Structure
**Brief:** Medical Director, Nursing leadership, Pharmacy oversight, Lab/diagnostics oversight, Health records management, ICT leadership, Clinical informatics, Data governance committee, Patient safety committee, Change control, Approval pathway.

| Aspect | Verdict | Detail |
|---|---|---|
| RBAC roles map to these roles | **Partial** | 8 groups approximate the governance structure but there's no actual committee configuration, oversight workflow, or approval pathways modeled. Governance exists only as Group names, not as workflows. |

### §9.2 Patient Safety Framework
**Brief:** Allergy alerts, drug interaction warning concept, duplicate order prevention, critical lab result alerts, critical imaging result alerts, abnormal vital sign triggers, pediatric dosing safeguards, duplicate patient record warning, mandatory fields for high-risk activities, time-stamped clinical notes, escalation alerts, user accountability (audit logs), alert prioritization.

| Aspect | Verdict | Detail |
|---|---|---|
| Allergy alerts | **Similar** | Critical block on keyword match. |
| Drug interaction warning concept | **Gap** | Not implemented. |
| Duplicate order prevention | **Gap** | No order-checking at encounter level (prescription duplicate exists, but order-level doesn't). |
| Critical lab result alerts | **Similar** | Auto-fire on LabResult.save(). |
| Critical imaging result alerts | **Similar** | Auto-fire on ImagingReport with is_critical_finding. |
| Abnormal vital sign triggers | **Similar** | 5 hard thresholds → AlertEvent. |
| Pediatric dosing safeguards | **Partial** | mg-only, DOB-dependent, no weight-based, no age-banded. |
| Duplicate patient record warning | **Similar** | Trigram + exact match, blocking interstitial. |
| Mandatory fields | **Partial** | `presenting_complaint` required on Encounter. Many clinical fields are optional. |
| Time-stamped clinical notes | **Similar** | Every write via `created_at` + HistoryRecords. |
| Escalation alerts | **Partial** | Alerts fire but no structured escalation (e.g., EWS > 5 → page senior). |
| User accountability (audit logs) | **Similar** | Every PHI write versioned with actor. |
| Alert prioritization | **Similar** | Critical (absolute block) vs warning (acknowledgeable). |

### §9.3 Legal, Ethical, Compliance
**Brief:** Malawi Electronic Transactions & Cyber Security Act 2016, Data Protection Act 2024, RBAC, strong authentication, audit trails + time-stamped entries, data minimization, controlled access, secure backup, privacy-by-design, HIPAA-informed best practices.

| Aspect | Verdict | Detail |
|---|---|---|
| Data Protection Act alignment | **Partial** | Encryption + consent flags + audit trails address core requirements. No explicit DPA compliance documentation. |
| Privacy-by-design | **Partial** | Field-level encryption covers sensitive fields. No formal privacy impact assessment documented. |
| Secure backup | **Gap** | No backup mechanism documented (Postgres dump is suggested but not automated). |

### §9.4 Cybersecurity Requirements
**Brief:** Secure login, MFA concept, RBAC, password policy, session timeout, encryption in transit, encryption at rest, access logging + failed login tracking, admin activity logging, backup/recovery plan, incident response plan, secure coding practices, SQLi/XSS/IDOR protection.

| Aspect | Verdict | Detail |
|---|---|---|
| Secure login | **Similar** | Django LoginView + CSRF middleware. |
| MFA concept | **Gap** | Not implemented. |
| RBAC | **Similar** | 8 groups + decorators. |
| Password policy (min 10) | **Similar** | Django validators. |
| Session timeout (15 min) | **Similar** | SESSION_COOKIE_AGE = 900s. |
| Encryption in transit | **Partial** | HTTPS in deployed env (Render + custom domain). Plain HTTP in Docker fallback (acceptable per AGENTS.md). |
| Encryption at rest (sensitive fields) | **Similar** | Fernet on National ID, phone, address. |
| Failed login tracking | **Similar** | django-axes (5 attempts, 15 min cooldown). |
| SQLi protection | **Similar** | Django ORM (parameterized queries). |
| XSS protection | **Similar** | Django template auto-escaping. |
| IDOR protection | **Partial** | Views check permissions but no per-object ownership checks in many views. |

### §9.5 Interoperability Standards
**Brief:** Ministry reporting systems, LIS/lab equipment interfaces, PACS/RIS design, pharmacy inventory/prescribing systems, mobile money + patient communication, API-ready architecture + standards-aware data modeling, OpenMRS reference.

| Aspect | Verdict | Detail |
|---|---|---|
| API-ready architecture | **Similar** | DRF endpoints. |
| Mobile money interfaces | **Similar** | Payment method + reference field. |
| Ministry reporting systems | **Gap** | No DHIS2/MaHIS integration. |
| Lab equipment interfaces | **Gap** | No LIS integration. |
| PACS/RIS design | **Gap** | Metadata-only. |
| Pharmacy systems integration | **Partial** | Internal only (no external pharmacy system API). |

---

## §10 System Resilience (Malawi Context)
**Brief:** Offline data entry, sync on reconnect, local server fallback, cloud/hybrid deployment, power outage recovery, data backup/restore testing, uptime monitoring, low-bandwidth optimization, use on standard laptops/tablets, simple hardware, local technical support, no data loss during interruptions.

| Aspect | Verdict | Detail |
|---|---|---|
| Offline data entry | **Similar** | IndexedDB queue with `data-offline-capable` attribute. |
| Sync on reconnect | **Similar** | `online` event → POST to `/api/sync/submit/`. |
| Idempotent replay | **Similar** | Client UUID + unique constraint + "already_applied" check. |
| Conflict detection | **Similar** | `SyncConflict` model + dispatch.py returns conflict_note. |
| Local server fallback | **Similar** | Docker Compose (Django + Postgres + Redis + Nginx). |
| Cloud deployment config | **Similar** | Render + Neon + Upstash specified. **Not confirmed deployed.** |
| Power outage recovery | **Similar** | Docker restart policies + atomic transactions. |
| Low-bandwidth optimization | **Similar** | Server-rendered HTML, vendored JS, no CDN. |
| Simple hardware | **Similar** | Django stack runs on standard laptops. |
| Service worker background sync | **Different** | SW has `sync` event listener but app.js doesn't listen for `syncNow` messages. Pipeline is half-wired. |

---

## §11 Workflow Design Requirements
**Brief:** Workflow diagrams for: Patient Journey, Nursing Workflow, Clinician Workflow, Laboratory Workflow, Medical Imaging Workflow, Pharmacy Workflow, Billing Workflow.

| Aspect | Verdict | Detail |
|---|---|---|
| Workflow diagrams | **Gap** | Zero diagrams of any type exist in the repository. No architecture diagram, ERD, data flow diagram, or deployment topology diagram. This is a significant gap for §19.3 deliverable. |

---

## §12 Prototype Minimum Requirements
**Brief:** User login, role-based dashboard, patient registration + search, patient profile, clinical encounter documentation, vital signs entry, lab order + result, imaging request + report concept, prescription + dispensing, basic billing + payment, dashboard/analytics, audit trail concept, backup/offline/local server concept.

| Aspect | Verdict | Detail |
|---|---|---|
| User login | **Similar** | LoginView + axes + password policy. |
| Role-based dashboard | **Similar** | Widget registry, role-gated nav. |
| Patient registration + search | **Similar** | Full Malawi-context, multi-word search, duplicate detection. |
| Patient profile (9 tabs) | **Similar** | Demographics, encounters, vitals, labs, imaging, pharmacy, billing, dialysis, admissions. |
| Clinical encounter | **Similar** | Sign + lock + addenda. |
| Vital signs + EWS | **Similar** | Full EWS + thresholds + alerts. |
| Lab order + result | **Similar** | 6-state workflow + critical alerts. |
| Imaging request + report | **Similar** | Pregnancy safety gate + critical alerts. |
| Prescription + dispensing | **Similar** | Safety checks + approval workflow + stock guard. |
| Basic billing + payment | **Similar** | Invoice + line items + mobile money. |
| Dashboard/analytics | **Similar** | 6-metric dashboard + per-module widgets. |
| Audit trail | **Partial** | simple-history on writes only. AlertEvent not historied. |
| Offline/sync/local concept | **Similar** | Service worker + IndexedDB + syncapi + Docker Compose. |
| No backup/restore testing | **Gap** | Backup mechanism not automated or tested. |

**Overall verdict on §12:** All requirements are met at least partially. The core MVP chain works end-to-end.

---

## §19 Expected Deliverables

| Deliverable | Status | Detail |
|---|---|---|
| §19.1 System Design Document | **Partial** | No single standalone document. Split across AGENTS.md + backend specs. |
| §19.2 Functional Prototype | **Similar** | Django app with 11 modules, 98 passing tests. |
| §19.3 Workflow Diagrams | **Gap** | Zero diagrams. |
| §19.4 Governance & Patient Safety Framework | **Partial** | No standalone document. Inline in AGENTS.md + code. |
| §19.5 Cybersecurity & Compliance Plan | **Partial** | Addressed in AGENTS.md §7. No standalone plan. |
| §19.6 Sustainability & Implementation Plan | **Gap** | No standalone plan. Implicit in AGENTS.md + hosting choices. |
| §19.7 Final Presentation & Demo | **Gap** | No presentation materials exist. |

---

## §20 Judging Criteria Cross-Check

| Criterion | Weight | Our Readiness | Risk |
|---|---|---|---|
| Clinical Relevance (20%) | 20% | **Strong.** MVP chain works end-to-end: registration → encounter → vitals → labs → imaging → pharmacy → billing. Malawi-context fields. | Low |
| Patient Safety (20%) | 20% | **Strong but has gaps.** Allergy alerts, critical results, EWS, audit trail all work. Missing: drug-drug interaction (high-severity gap), breastfeeding warning, pediatric dosing gaps. | Medium |
| Innovation (15%) | 15% | **Strong.** Offline-first sync architecture, dialysis module with missed-session heuristic, FHIR-lite export. | Low |
| Technical Design (15%) | 15% | **Strong.** Clean module boundaries, OpenAPI docs, dependency audit trail, dual deployment. Minus: no diagrams, no CI/CD config. | Low-Medium |
| Malawi Context Fit (15%) | 15% | **Strong.** Village/TA/district/region, age estimation, offline fallback, mobile money, low-bandwidth frontend. Minus: biometric-ready not implemented. | Low |
| Sustainability (15%) | 15% | **Medium.** Free-tier hosting, open-source stack, Docker Compose. Missing: standalone sustainability plan, training plan, CI/CD. | Medium |

---

## §22 Bonus Recognition Areas

| Bonus Area | Status | Detail |
|---|---|---|
| Strong UI design | **Similar** | Tailwind-based, clean, responsive. Subjective — judges may or may not agree. |
| Offline-first architecture | **Similar** | Full queue-and-replay pattern + service worker. |
| Strong accessibility | **Partial** | Basic form labels, semantic HTML. No explicit WCAG audit. |
| FHIR-aware data model | **Similar** | FHIR-Bundle export endpoint. |
| DICOM-aware imaging workflow | **Gap** | Metadata placeholder only. |
| LOINC-ready laboratory design | **Partial** | Field exists. Only 2/7 tests seeded with codes. |
| Advanced clinical decision support | **Partial** | Safety checks exist (allergy, duplicate, peds, pregnancy, renal). Missing: drug-drug interaction. |
| Safe pediatric workflows | **Partial** | Mg-only dose check. No weight-based, no age-banded, bypassed if DOB missing. |
| De-identified research export | **Gap** | Not implemented. |
| Strong data visualization | **Gap** | Tabular trends only. No charts. |

---

## §25 What a Strong Submission Looks Like

| Quality | Our Status | Detail |
|---|---|---|
| Clear understanding of hospital workflows | **Strong** | All core clinician/nurse/lab/pharmacy/billing workflows implemented. |
| Simple and intuitive UX | **Strong** | HTMX-based, fast, minimal JS. |
| Strong clinical safety thinking | **Medium** | Good foundations but missing drug-drug interaction (the biggest safety gap). |
| Realistic technical architecture | **Strong** | Django + DRF + HTMX + Tailwind. Well-modularized. |
| Sensitivity to infrastructure realities | **Strong** | Offline sync, Docker fallback, low-bandwidth design, vendored assets. |
| Clear path from prototype to implementation | **Medium** | Phase roadmaps exist in AGENTS.md. No deployment scripts (CI/CD). |
| Strong documentation | **Medium** | Good developer docs (AGENTS.md, COMPLETED_FEATURES.md, module specs). Missing: user manual, workflow diagrams, sustainability plan. |
| Feasible maintenance model | **Strong** | Open-source, Django is widely-known in Malawi dev community. |
| Evidence of testing with realistic scenarios | **Strong** | 98 tests, seed_demo with 5 patients and clinical journeys. |
| Support for teaching, service delivery, research | **Medium** | Teaching: consent_teaching flag only. Research: consent_research + de-identified export missing. |

---

## Summary: Critical Action Items (Ranked)

| Priority | Issue | Section | Impact |
|---|---|---|---|
| **P0** | Drug-drug interaction checking absent | §8.1.11, §9.2 | Patient Safety (20%) judging criterion — medication safety is core. |
| **P0** | AlertEvent not covered by django-simple-history | §8.1.16, §8.1.19 | Audit trail gap — alert acknowledgements invisible. |
| **P1** | No workflow diagrams anywhere | §11, §19.3 | Explicit deliverable requirement. |
| **P1** | No CI/CD configuration | §5 (AGENTS.md) | pip-audit requirement unenforceable without CI. |
| **P1** | Breastfeeding/lactation warning absent | §8.1.11, §9.2 | Patient Safety gap. |
| **P2** | Pediatric dosing: no weight-based, no age-banded, DOB-required bypass | §8.1.11, §9.2 | Malawi context: DOB often missing → check silently skips. |
| **P2** | Death documentation: discharge() always sets DISCHARGED, never DEAD | §8.1.4 | Bug in inpatient service. |
| **P2** | No MFA concept | §9.4 | Cybersecurity requirement. |
| **P2** | No idle-timer (13 min warning) | AGENTS.md §7 | Promised in architecture doc, not implemented. |
| **P2** | Profile template: references non-existent guardian_name/guardian_phone | §8.1.1 | Template bug — silent failure. |
| **P2** | No patient edit/update view | §8.1.1 | Once registered, data is immutable through UI. |
| **P3** | Allergy check ignores severity (mild = critical block) | §9.2 | Should differentiate mild vs anaphylaxis. |
| **P3** | LOINC codes: docs claim codes that aren't in seed data | §8.1.10 | Documentation inconsistency. |
| **P3** | Encounter lacks structured Review of Systems field | §8.1.3 | Minor — clinicians use exam_findings. |
| **P3** | No biometric-ready design | §8.1.1 | Judging bonus item. |
| **P3** | consent_data_use missing | §8.1.1 | Brief requires it. |
| **P3** | No standalone sustainability plan or training plan | §19.6 | Explicit deliverables. |
| **P3** | Cancel prescription: status exists but no UI/view | §8.1.11 | Workflow gap. |
| **P3** | Nav gating uses Profile.role, view enforcement uses Group | §7.6 | Can diverge; race condition in seed creation. |
| **P3** | SW background sync listener not wired to replay handler | §10 | Offline pipeline half-connected. |
| **P3** | Cloud deployment not confirmed live | §10 | Need to verify before demo day. |
| **P3** | No MUST/GSL logo files in static assets | §24 | Submission rules require logos on every page. |
| **P3** | No hash-pinned requirements.txt (only .in exists) | §5 (AGENTS.md) | Supply-chain audit requirement. |

---

## Verdict

**What we do well:** The MVP chain is complete and well-integrated. Registration → encounter → vitals → labs → imaging → pharmacy → billing flows end-to-end. The offline sync architecture (service worker + IndexedDB + syncapi + conflict detection) is a genuine innovation differentiator. Malawi context fields (TA, village, age_estimated, mobile money) demonstrate real contextual awareness. 98 passing tests show engineering rigor.

**What we need to fix before demo day:** Drug-drug interaction checking (P0 — judges WILL ask about medication safety) and AlertEvent audit trail (P0 — governance question). Workflow diagrams (P1 — explicit deliverable). Breastfeeding warning (P1 — gaps in medication safety). The death-documentation bug in inpatient discharge (P2 — looks sloppy if caught).

**What judges will notice:** The strong offline story, the clean HTMX frontend (fast, no SPA overhead), the dialysis module (bonus points, well-implemented), the audit trail coverage. They will also notice: no drug interaction checking, no MFA (concept only), no diagrams, no CI/CD.
