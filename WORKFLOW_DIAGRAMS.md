# Workflow Diagrams

This document maps the implemented prototype into the challenge brief's required workflow areas.

## 1. Patient Registration and MPI

Flow:
- Open patient registration
- Capture demographics, identifiers, contacts, and consent data
- Check for duplicates
- Create or update the master patient record
- Redirect to profile or downstream service

Implemented in:
- `patients`
- `templates/patients/register.html`
- `templates/patients/profile.html`

## 2. Outpatient Encounter Flow

Flow:
- Open patient profile
- Start encounter documentation
- Record complaint, history, examination, diagnosis, and plan
- Save orders, prescriptions, and follow-up actions

Implemented in:
- `encounters`
- `templates/encounters/*`

## 3. Inpatient Admission and Ward Flow

Flow:
- Admit patient from profile or encounter
- Allocate ward and bed
- Track ward round notes, nursing care, fluids, MAR, procedures, and discharge planning

Implemented in:
- `inpatient`
- `inpatient/templates/inpatient/*`

## 4. Emergency and Triage Flow

Flow:
- Rapid register unstable patient
- Capture triage category and emergency observations
- Escalate to ward, imaging, lab, or admission

Implemented in:
- `emergency`
- `emergency/templates/emergency/*`

## 5. Nursing Documentation Flow

Flow:
- Record assessment
- Capture nursing problems and interventions
- Document care plans and progress
- Escalate abnormal findings

Implemented in:
- `inpatient`
- `templates/inpatient/nursing_assessment_*`

## 6. Vital Signs and Abnormal Alert Flow

Flow:
- Capture temperature, pulse, blood pressure, respiratory rate, oxygen saturation, and other observations
- Generate alerts for abnormal values
- Surface trends on the dashboard and patient profile

Implemented in:
- `vitals`
- `reporting`
- `templates/vitals/*`
- `templates/reporting/*`

## 7. Laboratory Ordering and Result Review

Flow:
- Place lab orders
- Collect samples
- Record results
- Review abnormal findings

Implemented in:
- `laboratory`
- `templates/laboratory/*`

## 8. Imaging Request and Report Flow

Flow:
- Request imaging
- Assign modality
- Record report
- Review worklist and results

Implemented in:
- `imaging`
- `templates/imaging/*`

## 9. Pharmacy Prescribing and Dispensing Flow

Flow:
- Create prescription
- Run medication safety checks
- Queue dispensing
- Dispense or resolve prescription issues

Implemented in:
- `pharmacy`
- `templates/pharmacy/*`

## 10. Billing and Invoice Flow

Flow:
- Generate invoice
- Track payment state
- View billing dashboard and patient invoice history

Implemented in:
- `billing`
- `templates/billing/*`

## 11. Dialysis Session Recording Flow

Flow:
- View active prescriptions
- Record a completed dialysis session
- Track access type and completion status

Implemented in:
- `dialysis`
- `dialysis/templates/dialysis/*`

## Cross-Cutting Views

- `accounts/dashboard.html` provides the role-aware launch point for these flows.
- `reporting/analytics_dashboard.html` provides the operational overview.
- `accounts/control_panel.html` supports administrative oversight.

