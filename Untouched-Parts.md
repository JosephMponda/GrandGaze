# Untouched Parts — Specifications Not Yet Implemented

**Date:** 2026-07-09  
**Source:** `MUST_GSL EMR Innovation Challenge Brief v31'05'2026.pdf`  
**Purpose:** Track every brief specification with zero implementation, to guide remaining development sprints.

**Last updated:** 2026-07-09 — 9 items implemented.

---

## §8.1 Core Modules — Missing Sub-items

These are specifications within the **required** Core Modules (§8.1) that have no code whatsoever.

### 8.1.2 Appointment, Queue, and Patient Flow Management

| Brief Ref | Requirement | Priority | Status |
|-----------|-------------|----------|--------|
| a | Appointment booking and clinic scheduling | HIGH | **OPEN** — required for outpatient workflow completeness |
| b | Walk-in visit registration | MEDIUM | **OPEN** — partly covered by emergency rapid registration |
| c | Provider scheduling | MEDIUM | **OPEN** |
| d | Patient check-in and check-out | HIGH | **OPEN** — needed for queue flow |
| f | Emergency fast-track workflow (distinct from triage) | MEDIUM | **OPEN** |
| g | Referral to another department (UI workflow) | HIGH | **DONE** — referral create/view UI added (2026-07-09) |
| h | Missed appointment tracking | MEDIUM | **OPEN** — depends on appointment system |
| i | Follow-up appointment generation | MEDIUM | **OPEN** — depends on appointment system |
| j | SMS or mobile notification concept | LOW | **OPEN** — stretch feature |

### 8.1.4 Inpatient and Ward Management

| Brief Ref | Requirement | Priority | Status |
|-----------|-------------|----------|--------|
| e | Nursing care plans | HIGH | **DONE** — model, service, views, templates (2026-07-09) |
| f | Fluid balance charts and intake-output monitoring | HIGH | **DONE** — model, service, views, templates with intake/output/sum (2026-07-09) |
| g | Medication Administration Record (MAR) | HIGH | **DONE** — model, service, views, templates linking prescriptions to administration events (2026-07-09) |
| i | Procedure notes | HIGH | **DONE** — model, service, views, templates (2026-07-09) |
| k | Death documentation (death certificate, cause of death) | MEDIUM | **DONE** — cause_of_death + death_certificate_issued fields on Admission; conditional UI in discharge form (2026-07-09) |

### 8.1.5 Emergency and Triage

| Brief Ref | Requirement | Priority | Status |
|-----------|-------------|----------|--------|
| d | Resuscitation notes and trauma notes | MEDIUM | **OPEN** |
| e | Time-critical event recording | MEDIUM | **OPEN** — door-to-needle, door-to-balloon timestamps |
| f | Referral to theatre, ICU, imaging, lab, ward (from emergency) | MEDIUM | **OPEN** |

### 8.1.6 Nursing Documentation and Care Coordination

| Brief Ref | Requirement | Priority | Status |
|-----------|-------------|----------|--------|
| a | Nursing assessment and nursing problem list | HIGH | **DONE** — model with JSONField for problem list, views, templates (2026-07-09) |
| b | Nursing notes and care plans | HIGH | **DONE** — same as §8.1.4(e) |
| d | Fall risk and pressure sore risk assessment | MEDIUM | **OPEN** |
| e | Wound care documentation | MEDIUM | **OPEN** |
| f | Medication Administration Record (MAR) | HIGH | **DONE** — same as §8.1.4(g) |
| g | Nursing handover | MEDIUM | **OPEN** |
| i | Patient education and discharge counselling notes | MEDIUM | **OPEN** |

### 8.1.7 Vital Signs — Missing Sub-items

| Brief Ref | Requirement | Priority | Status |
|-----------|-------------|----------|--------|
| e | Pediatric age-adjusted vital sign alerts | MEDIUM | **DONE** — age-band EWS scoring + hard-alert thresholds for 4 pediatric age groups (2026-07-09) |

### 8.1.8 Physician/Provider Documentation — Missing Sub-items

| Brief Ref | Requirement | Priority | Status |
|-----------|-------------|----------|--------|
| a | Dedicated History & Physical (H&P) template | MEDIUM | **OPEN** |
| e | Procedure Notes | HIGH | **DONE** — same as §8.1.4(i) |
| g | Medication Reconciliation | MEDIUM | **OPEN** |
| h | Structured clinical decision-making documentation | LOW | **OPEN** |

### 8.1.9 Provider Workflow — Missing Sub-items

| Brief Ref | Requirement | Priority | Status |
|-----------|-------------|----------|--------|
| c | Interdisciplinary communication tools (messaging) | MEDIUM | **OPEN** |

### 8.1.10 Laboratory — Missing Sub-items

| Brief Ref | Requirement | Priority | Status |
|-----------|-------------|----------|--------|
| h | Reagent and consumables inventory | LOW | **OPEN** — stretch |
| i | Quality control documentation | LOW | **OPEN** |
| j | Linkage to external/referral laboratories | LOW | **OPEN** |

### 8.1.11 Pharmacy — Missing Sub-items

| Brief Ref | Requirement | Priority | Status |
|-----------|-------------|----------|--------|
| l | Controlled medicines tracking (special approval workflow) | MEDIUM | **OPEN** — Drug.is_controlled field exists, workflow missing |

### 8.1.13 ICU/HDU/Critical Care

| Brief Ref | Requirement | Priority | Status |
|-----------|-------------|----------|--------|
| a | ICU/HDU admission note | MEDIUM | **OPEN** |
| b | Continuous observation charting | LOW | **OPEN** — stretch |
| c | Ventilation status and oxygen therapy documentation | MEDIUM | **OPEN** |
| d | Fluid balance and infusion monitoring | MEDIUM | **OPEN** |
| e | Inotropes, sedation, critical care medications | MEDIUM | **OPEN** |
| f | Critical care procedure notes | MEDIUM | **OPEN** |
| g | Sepsis alert concept | MEDIUM | **OPEN** |
| i | Nursing care plans and daily ICU review | MEDIUM | **OPEN** |
| j | ICU discharge summary | MEDIUM | **OPEN** |
| k | Mortality and morbidity review dashboard | MEDIUM | **OPEN** |

### 8.1.14 Billing — Missing Sub-items

| Brief Ref | Requirement | Priority | Status |
|-----------|-------------|----------|--------|
| c | Printable invoice/receipt generation | MEDIUM | **DONE** — print view with browser print styling (2026-07-09) |
| f | Waiver/exemption approval workflow (separate from flag) | LOW | **OPEN** |
| g | Revenue totals and unpaid bills report | MEDIUM | **OPEN** |

### 8.1.15 Inventory, Supplies, Equipment — Missing Sub-items

| Brief Ref | Requirement | Priority | Status |
|-----------|-------------|----------|--------|
| b | Stock expiry tracking | LOW | **OPEN** |
| c | Batch tracking | LOW | **OPEN** |
| d | Equipment maintenance records | LOW | **OPEN** |
| e | Biomedical equipment downtime reporting | LOW | **OPEN** |
| f | Clinical use → inventory consumption linkage | LOW | **OPEN** |

### 8.1.16 Clinical Governance — Missing Sub-items

| Brief Ref | Requirement | Priority | Status |
|-----------|-------------|----------|--------|
| a | Documentation compliance dashboard | LOW | **OPEN** |
| c | Regulatory/accreditation requirements mapping | LOW | **OPEN** |

### 8.1.17 Multidisciplinary Coordination — Missing Sub-items

| Brief Ref | Requirement | Priority | Status |
|-----------|-------------|----------|--------|
| c | Allied health documentation | LOW | **OPEN** |
| d | Case management and discharge planning collaboration | LOW | **OPEN** |

### 8.1.18 Health Information Exchange — Missing Sub-items

| Brief Ref | Requirement | Priority | Status |
|-----------|-------------|----------|--------|
| c | DICOM-ready imaging integration | LOW | **OPEN** — future module by brief definition |
| f | Ministry of Health reporting system linkage | LOW | **OPEN** |
| g | National digital health infrastructure linkage | LOW | **OPEN** |
| h | Laboratory equipment interfaces | LOW | **OPEN** |
| j | mHealth application integration | LOW | **OPEN** |
| k | Secure bulk data export/import | MEDIUM | **OPEN** |

### 8.1.19 Administration — Missing Sub-items

| Brief Ref | Requirement | Priority | Status |
|-----------|-------------|----------|--------|
| f | Data backup monitoring dashboard | LOW | **OPEN** |
| g | System usage reports | LOW | **OPEN** |
| h | Change control log | LOW | **OPEN** |
| i | Incident reporting system | LOW | **OPEN** |
| j | Downtime reporting | LOW | **OPEN** |
| k | Data governance dashboard | LOW | **OPEN** |

---

## §8.2 Future Modules — Not Implemented

These are labelled **Future Modules** in the brief (§8.2). None are expected for MVP but are tracked for roadmap.

| Module | What's Missing | Demo-Day Impact |
|--------|---------------|-----------------|
| 8.2.1 | Digital Medical Imaging (PACS/RIS integration, DICOM, teaching repository) | LOW — request/report MVP stubs exist |
| 8.2.2 | Theatre, Anaesthesia, Procedure Management | LOW — not in MVP scope |
| 8.2.3 | Maternal, Neonatal, Child Health | LOW — not in MVP scope |
| 8.2.4 | Other Specialist Clinics (templates for 15+ specialties) | LOW — not in MVP scope |
| 8.2.5 | Oncology and Cancer Care | LOW — not in MVP scope |
| 8.2.6 | Blood Bank and Transfusion | LOW — not in MVP scope |
| 8.2.7 | Infection Prevention, Antimicrobial Stewardship, Public Health | LOW — not in MVP scope |
| 8.2.8 | Rehabilitation, Physiotherapy, Allied Health | LOW — not in MVP scope |
| 8.2.9 | Teaching, Training, Simulation | MEDIUM — judges may ask about education use |
| 8.2.10 | Research, Audit, Quality Improvement | MEDIUM — judges may ask about research use |

---

## §9 Mandatory Enhancements — Gaps

### 9.1 Clinical Governance Structure
- No documented governance workflows, committee structures, or change control process in the codebase or docs.

### 9.3 Legal/Ethical/Compliance
- No explicit mapping to Malawi Electronic Transactions and Cyber Security Act.
- No formal Data Protection Impact Assessment.
- No backup/restore documented procedure.

### 9.4 Cybersecurity
- **Multi-factor authentication** — documented in `docs/mfa.md` but not implemented.
- Encryption of data in transit — `SECURE_SSL_REDIRECT` not enabled, no HSTS.
- Backup and recovery plan — no documented procedure.
- Incident response plan — no documented procedure.

### 9.5 Interoperability
- No Ministry of Health report generation or export.
- No actual mobile money API integration (field exists).
- No laboratory equipment interface.
- No PACS/RIS integration (AGENTS.md correctly defers).

---

## §10 System Resilience — Gaps

- Actual IndexedDB queue write-back logic not fully implemented (service worker registered, form attributes set, sync endpoint exists — but the queue-replay loop in `app.js` is skeletal).
- No documented backup/restore testing procedure.
- No uptime monitoring.
- No local technical support documentation.

---

## §11 Workflow Diagrams — Not Implemented

**All 7 required workflow diagrams are missing:**

| Brief Ref | Required Diagram | Status |
|-----------|-----------------|--------|
| 11.1 | Patient Journey | **EXISTS** in `docs/workflows/01-patient-journey.md` |
| 11.2 | Nursing Workflow | **EXISTS** in `docs/workflows/02-nursing-workflow.md` |
| 11.3 | Clinician Workflow | **EXISTS** in `docs/workflows/03-clinician-workflow.md` |
| 11.4 | Laboratory Workflow | **EXISTS** in `docs/workflows/04-laboratory-workflow.md` |
| 11.5 | Medical Imaging Workflow | **EXISTS** in `docs/workflows/05-imaging-workflow.md` |
| 11.6 | Pharmacy Workflow | **EXISTS** in `docs/workflows/06-pharmacy-workflow.md` |
| 11.7 | Billing Workflow | **EXISTS** in `docs/workflows/07-billing-workflow.md` |

---

## Summary — Priority Order for Remaining Sprint

| Priority | Items | Status |
|----------|-------|--------|
| **P0 — Demo blockers** | Workflow diagrams (7) | **DONE** — all 7 exist |
| **P1 — Clinical workflow gaps** | MAR, nursing care plans, fluid balance, procedure notes | **DONE** (2026-07-09) |
| **P2 — Patient safety gaps** | Pediatric vital sign alerts, appointment scheduling, check-in/out | Pediatric alerts **DONE**; scheduling/check-in **OPEN** |
| **P3 — Offline completion** | IndexedDB queue replay, backup documentation | **OPEN** |
| **P4 — Future modules (8.2.x)** | Teaching/research support for judging questions | **OPEN** |
| **P5 — Additional completions** | Death documentation, referral UI, printable invoices, nursing assessment | **DONE** (2026-07-09) |
