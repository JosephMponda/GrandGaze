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

## After Changes
- Hard refresh browser
- Test with network off
