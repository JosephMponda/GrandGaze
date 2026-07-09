# Untouched Parts — Specifications Not Yet Implemented

**Date:** 2026-07-09  
**Source:** `MUST_GSL EMR Innovation Challenge Brief v31'05'2026.pdf`  
**Purpose:** Track every brief specification with zero implementation, to guide remaining development sprints.

---

## §8.1 Core Modules — Missing Sub-items

These are specifications within the **required** Core Modules (§8.1) that have no code whatsoever.

### 8.1.2 Appointment, Queue, and Patient Flow Management

| Brief Ref | Requirement | Priority |
|-----------|-------------|----------|
| a | Appointment booking and clinic scheduling | HIGH — required for outpatient workflow completeness |
| b | Walk-in visit registration | MEDIUM — partly covered by emergency rapid registration |
| c | Provider scheduling | MEDIUM |
| d | Patient check-in and check-out | HIGH — needed for queue flow |
| f | Emergency fast-track workflow (distinct from triage) | MEDIUM |
| g | Referral to another department (UI workflow) | HIGH — model exists, UI missing |
| h | Missed appointment tracking | MEDIUM — depends on appointment system |
| i | Follow-up appointment generation | MEDIUM — depends on appointment system |
| j | SMS or mobile notification concept | LOW — stretch feature |

### 8.1.4 Inpatient and Ward Management

| Brief Ref | Requirement | Priority |
|-----------|-------------|----------|
| e | Nursing care plans | HIGH — required for ward workflow |
| f | Fluid balance charts and intake-output monitoring | HIGH — required for inpatient care |
| g | Medication Administration Record (MAR) | HIGH — required for medication safety |
| i | Procedure notes | HIGH — required for surgical/procedural documentation |
| k | Death documentation (death certificate, cause of death) | MEDIUM |

### 8.1.5 Emergency and Triage

| Brief Ref | Requirement | Priority |
|-----------|-------------|----------|
| d | Resuscitation notes and trauma notes | MEDIUM |
| e | Time-critical event recording | MEDIUM — door-to-needle, door-to-balloon timestamps |
| f | Referral to theatre, ICU, imaging, lab, ward (from emergency) | MEDIUM |

### 8.1.6 Nursing Documentation and Care Coordination

| Brief Ref | Requirement | Priority |
|-----------|-------------|----------|
| a | Nursing assessment and nursing problem list | HIGH |
| b | Nursing notes and care plans | HIGH |
| d | Fall risk and pressure sore risk assessment | MEDIUM |
| e | Wound care documentation | MEDIUM |
| f | Medication Administration Record (MAR) | HIGH — duplicate of 8.1.4(g) |
| g | Nursing handover | MEDIUM |
| i | Patient education and discharge counselling notes | MEDIUM |

### 8.1.7 Vital Signs — Missing Sub-items

| Brief Ref | Requirement | Priority |
|-----------|-------------|----------|
| e | Pediatric age-adjusted vital sign alerts | MEDIUM — improves patient safety scoring |

### 8.1.8 Physician/Provider Documentation — Missing Sub-items

| Brief Ref | Requirement | Priority |
|-----------|-------------|----------|
| a | Dedicated History & Physical (H&P) template | MEDIUM |
| e | Procedure Notes | HIGH — duplicate of 8.1.4(i) |
| g | Medication Reconciliation | MEDIUM |
| h | Structured clinical decision-making documentation | LOW |

### 8.1.9 Provider Workflow — Missing Sub-items

| Brief Ref | Requirement | Priority |
|-----------|-------------|----------|
| c | Interdisciplinary communication tools (messaging) | MEDIUM |

### 8.1.10 Laboratory — Missing Sub-items

| Brief Ref | Requirement | Priority |
|-----------|-------------|----------|
| h | Reagent and consumables inventory | LOW — stretch |
| i | Quality control documentation | LOW |
| j | Linkage to external/referral laboratories | LOW |

### 8.1.11 Pharmacy — Missing Sub-items

| Brief Ref | Requirement | Priority |
|-----------|-------------|----------|
| l | Controlled medicines tracking (special approval workflow) | MEDIUM — Drug.is_controlled field exists, workflow missing |

### 8.1.13 ICU/HDU/Critical Care

| Brief Ref | Requirement | Priority |
|-----------|-------------|----------|
| a | ICU/HDU admission note | MEDIUM |
| b | Continuous observation charting | LOW — stretch |
| c | Ventilation status and oxygen therapy documentation | MEDIUM |
| d | Fluid balance and infusion monitoring | MEDIUM |
| e | Inotropes, sedation, critical care medications | MEDIUM |
| f | Critical care procedure notes | MEDIUM |
| g | Sepsis alert concept | MEDIUM |
| i | Nursing care plans and daily ICU review | MEDIUM |
| j | ICU discharge summary | MEDIUM |
| k | Mortality and morbidity review dashboard | MEDIUM |

### 8.1.14 Billing — Missing Sub-items

| Brief Ref | Requirement | Priority |
|-----------|-------------|----------|
| c | Printable invoice/receipt generation | MEDIUM |
| f | Waiver/exemption approval workflow (separate from flag) | LOW |
| g | Revenue totals and unpaid bills report | MEDIUM |

### 8.1.15 Inventory, Supplies, Equipment — Missing Sub-items

| Brief Ref | Requirement | Priority |
|-----------|-------------|----------|
| b | Stock expiry tracking | LOW |
| c | Batch tracking | LOW |
| d | Equipment maintenance records | LOW |
| e | Biomedical equipment downtime reporting | LOW |
| f | Clinical use → inventory consumption linkage | LOW |

### 8.1.16 Clinical Governance — Missing Sub-items

| Brief Ref | Requirement | Priority |
|-----------|-------------|----------|
| a | Documentation compliance dashboard | LOW |
| c | Regulatory/accreditation requirements mapping | LOW |

### 8.1.17 Multidisciplinary Coordination — Missing Sub-items

| Brief Ref | Requirement | Priority |
|-----------|-------------|----------|
| c | Allied health documentation | LOW |
| d | Case management and discharge planning collaboration | LOW |

### 8.1.18 Health Information Exchange — Missing Sub-items

| Brief Ref | Requirement | Priority |
|-----------|-------------|----------|
| c | DICOM-ready imaging integration | LOW — future module by brief definition |
| f | Ministry of Health reporting system linkage | LOW |
| g | National digital health infrastructure linkage | LOW |
| h | Laboratory equipment interfaces | LOW |
| j | mHealth application integration | LOW |
| k | Secure bulk data export/import | MEDIUM |

### 8.1.19 Administration — Missing Sub-items

| Brief Ref | Requirement | Priority |
|-----------|-------------|----------|
| f | Data backup monitoring dashboard | LOW |
| g | System usage reports | LOW |
| h | Change control log | LOW |
| i | Incident reporting system | LOW |
| j | Downtime reporting | LOW |
| k | Data governance dashboard | LOW |

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
| 11.1 | Patient Journey (registration→triage→consultation→orders→diagnosis→treatment→pharmacy→billing→follow-up→referral/admission/discharge/death) | ❌ No file exists |
| 11.2 | Nursing Workflow (triage→vitals→nursing notes→MAR→escalation→handover) | ❌ No file exists |
| 11.3 | Clinician Workflow (patient review→documentation→diagnosis→orders→prescribing→result review→discharge/follow-up) | ❌ No file exists |
| 11.4 | Laboratory Workflow (order receipt→sample collection→result entry→verification→critical alert) | ❌ No file exists |
| 11.5 | Medical Imaging Workflow (request→safety checks→scheduling→acquisition→reporting→critical alert→clinician review) | ❌ No file exists |
| 11.6 | Pharmacy Workflow (prescription receipt→allergy/interaction check→dispensing→stock status→record) | ❌ No file exists |
| 11.7 | Billing Workflow (service capture→invoice→payment→receipt→revenue reporting) | ❌ No file exists |

---

## Summary — Priority Order for Remaining Sprint

| Priority | Items | Effort Estimate |
|----------|-------|----------------|
| **P0 — Demo blockers** | Workflow diagrams (7), MFA doc | 1–2 days |
| **P1 — Clinical workflow gaps** | MAR, nursing care plans, fluid balance, procedure notes | 2–3 days |
| **P2 — Patient safety gaps** | Pediatric vital sign alerts, appointment scheduling, check-in/out | 1–2 days |
| **P3 — Offline completion** | IndexedDB queue replay, backup documentation | 1 day |
| **P4 — Future modules (8.2.x)** | Teaching/research support for judging questions | 1–2 days |
