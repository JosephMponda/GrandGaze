# OFFLINE PHASE 1 - Implementation Guide

## Goal
Make key clinical forms work offline and improve user feedback.

## Changes Required

### 1. static/js/app.js
- Strengthen offline form interception
- Reduce toast spam
- Ensure queue works reliably

### 2. Templates
- Add `data-offline-capable="true"` and `data-form-type` to critical forms

### 3. Base template
- Improve offline banner

## Status: COMPLETE

All 24 clinical forms now have both `data-offline-capable="true"` and a matching `data-form-type`.

### Forms with offline support (24 total)

| Module | Template | form_type |
|---|---|---|
| Patients | register.html | patient_registration |
| Encounters | new.html | encounter_note |
| Vitals | entry.html | vitals_entry |
| Inpatient | admission_detail.html | ward_round_note |
| Inpatient | mar_entry.html | mar_entry |
| Inpatient | care_plan_form.html | care_plan_create |
| Inpatient | care_plan_list.html | care_plan_evaluate |
| Inpatient | fluid_balance.html | fluid_balance_entry |
| Inpatient | procedure_note_form.html | procedure_note |
| Inpatient | nursing_assessment_form.html | nursing_assessment |
| Inpatient | create_referral.html | referral |
| Pharmacy | prescribe.html | pharmacy_prescribe |
| Pharmacy | queue.html | pharmacy_approve |
| Pharmacy | dispense.html | pharmacy_dispense |
| Laboratory | order.html | lab_order |
| Laboratory | collect.html | lab_collect |
| Laboratory | result_form.html | lab_result |
| Laboratory | result_detail.html | lab_verify |
| Imaging | request.html | imaging_request |
| Imaging | report_form.html | imaging_report |
| Emergency | triage_form.html | triage |
| Emergency | resolve.html | resolve_triage |
| Dialysis | create_prescription.html | dialysis_prescription |
| Dialysis | record_session.html | dialysis_session |

## Audit Fixes Applied (11 issues)

| # | Issue | Fix | File |
|---|-------|-----|------|
| 1 | Drug lookup used wrong IndexedDB store | Changed `get('prescriptions', ...)` to `get('drugs', ...)` | `offline-client.js:342` |
| 2 | `parseInt("server:5")` returned NaN | Replaced with `delete data.drug_id/test_id/modality_id` before create | `offline-client.js` |
| 3 | SW cached stale version URLs | Updated `APP_SHELL` with current version strings | `sw.js:1-10` |
| 4 | Lab orders missing `status: 'ordered'` | Added default status in `createLabOrder` | `offline-client.js:162` |
| 5 | Unused `id` variables | Removed from `evaluateCarePlan`, `approvePrescription`, `dispensePrescription` | `offline-client.js` |
| 6 | `app.js` sent full queue item | Now sends only `{client_uuid, form_type, payload_json}` | `app.js:179` |
| 7 | Page cache never cleared | SW activate now clears `PAGE_CACHE` on version update | `sw.js:17-21` |
| 9 | XSS via unescaped form title | `form()` now uses `escape(title)` | `offline-client.js:613` |
| 11 | Inconsistent sync payload format | Fixed to match serializer expectations | `app.js:179` |
| 12 | Missing status defaults | Added `status: 'requested'` (imaging), `is_active: true` (dialysis) | `offline-client.js` |
| 13 | Bootstrap missing triage/dialysis data | Added to both server view and client bootstrap | `syncapi/views.py`, `offline-client.js` |

## Accepted Trade-offs

| # | Issue | Reason |
|---|-------|--------|
| 8 | Two separate sync queues | By design — `app.js` handles online-first forms, `offline-client.js` handles local-first workspace |
| 10 | CSRF token in localStorage | Required for offline-first sync; can't use cookies when server is down |

## After Changes
- Hard refresh browser
- Test with network off