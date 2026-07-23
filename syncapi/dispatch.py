"""Dispatch table mapping form_type -> handler function.

Each handler receives (payload_json, submitted_by) and returns
(record_or_none, conflict_description_or_none).
"""

from django.db import transaction

from encounters.forms import EncounterForm
from vitals.forms import VitalSignSetForm

from patients.services import check_possible_duplicate, confirm_not_duplicate, register_patient
from patients.forms import PatientRegistrationForm


def _validated_payload(form_class, payload):
    """Apply the same ModelForm validation used by online clinical workflows."""
    form = form_class(payload)
    if not form.is_valid():
        raise ValueError(form.errors.get_json_data())
    return form.cleaned_data


def _handle_patient_registration(payload, submitted_by):
    # Same safety gate as the online registration view (patients/views.py) -
    # register_patient() itself does NOT run this check, so every caller
    # must. Skipping it here would let offline-synced registrations bypass
    # duplicate-patient detection entirely.
    confirmed_id = payload.get("confirmed_not_duplicate_of")
    patient_data = _validated_payload(PatientRegistrationForm, payload)
    duplicates = check_possible_duplicate(patient_data)
    confirmed = duplicates.filter(pk=confirmed_id).first() if confirmed_id else None
    remaining = duplicates.exclude(pk=confirmed.pk) if confirmed else duplicates
    if remaining.exists() or (confirmed_id and not confirmed):
        candidates = ", ".join(p.patient_number for p in remaining[:5])
        return None, f"Possible duplicate patient(s): {candidates}. Confirm on next sync."

    patient = register_patient(patient_data, registered_by=submitted_by)
    if confirmed:
        confirm_not_duplicate(patient, confirmed, confirmed_by=submitted_by)
    return patient, None


def _handle_encounter_note(payload, submitted_by):
    from encounters.services import create_encounter
    from patients.models import Patient

    patient = Patient.objects.get(pk=payload["patient_id"])
    encounter = create_encounter(patient=patient, clinician=submitted_by, data=_validated_payload(EncounterForm, payload))
    return encounter, None


def _handle_vitals_entry(payload, submitted_by):
    from encounters.models import Encounter
    from vitals.services import record_vitals

    encounter = Encounter.objects.get(pk=payload["encounter_id"])
    if encounter.signed_at:
        return None, f"Encounter #{encounter.pk} is already signed; cannot add vitals."
    vitals = record_vitals(encounter=encounter, recorded_by=submitted_by, data=_validated_payload(VitalSignSetForm, payload))
    return vitals, None


# ── Inpatient handlers (§8.1.4) ──────────────────────────────────────────


def _handle_ward_round_note(payload, submitted_by):
    from inpatient.forms import WardRoundNoteForm
    from inpatient.models import Admission
    from inpatient.services import add_ward_round_note

    admission = Admission.objects.get(pk=payload["admission_id"])
    if admission.status != "active":
        return None, f"Admission #{admission.pk} is no longer active."
    data = _validated_payload(WardRoundNoteForm, payload)
    note = add_ward_round_note(admission, submitted_by, **data)
    return note, None


def _handle_mar_entry(payload, submitted_by):
    from inpatient.models import Admission
    from inpatient.services import record_administration
    from pharmacy.models import Prescription

    admission = Admission.objects.get(pk=payload["admission_id"])
    if admission.status != "active":
        return None, f"Admission #{admission.pk} is no longer active."
    prescription = Prescription.objects.get(pk=payload["prescription"])
    from inpatient.forms import MAREntryForm
    data = _validated_payload(MAREntryForm, payload)
    data.pop("prescription")
    entry = record_administration(admission, prescription, submitted_by, **data)
    return entry, None


def _handle_care_plan_create(payload, submitted_by):
    from inpatient.models import Admission
    from inpatient.services import create_care_plan

    admission = Admission.objects.get(pk=payload["admission_id"])
    if admission.status != "active":
        return None, f"Admission #{admission.pk} is no longer active."
    from inpatient.forms import CarePlanForm
    data = _validated_payload(CarePlanForm, payload)
    plan = create_care_plan(admission, submitted_by, **data)
    return plan, None


def _handle_care_plan_evaluate(payload, submitted_by):
    from inpatient.models import NursingCarePlan
    from inpatient.services import evaluate_care_plan

    plan = NursingCarePlan.objects.get(pk=payload["care_plan_id"])
    from inpatient.forms import CarePlanEvaluateForm
    data = _validated_payload(CarePlanEvaluateForm, payload)
    data.pop("care_plan_id")
    evaluated = evaluate_care_plan(plan, submitted_by, **data)
    return evaluated, None


def _handle_fluid_balance_entry(payload, submitted_by):
    from inpatient.models import Admission
    from inpatient.services import record_fluid

    admission = Admission.objects.get(pk=payload["admission_id"])
    if admission.status != "active":
        return None, f"Admission #{admission.pk} is no longer active."
    from inpatient.forms import FluidBalanceEntryForm
    data = _validated_payload(FluidBalanceEntryForm, payload)
    entry = record_fluid(admission, submitted_by, data["fluid_type"], data["volume_ml"])
    return entry, None


def _handle_procedure_note(payload, submitted_by):
    from inpatient.models import Admission
    from inpatient.services import create_procedure_note

    admission = Admission.objects.get(pk=payload["admission_id"])
    if admission.status != "active":
        return None, f"Admission #{admission.pk} is no longer active."
    from inpatient.forms import ProcedureNoteForm
    data = _validated_payload(ProcedureNoteForm, payload)
    note = create_procedure_note(admission, submitted_by, **data)
    return note, None


def _handle_nursing_assessment(payload, submitted_by):
    from inpatient.models import Admission
    from inpatient.services import create_nursing_assessment

    admission = Admission.objects.get(pk=payload["admission_id"])
    if admission.status != "active":
        return None, f"Admission #{admission.pk} is no longer active."
    from inpatient.forms import NursingAssessmentForm
    data = _validated_payload(NursingAssessmentForm, payload)
    assessment = create_nursing_assessment(admission, submitted_by, **data)
    return assessment, None


def _handle_referral(payload, submitted_by):
    from patients.models import Patient, ReferralRecord

    patient = Patient.objects.get(pk=payload["patient_id"])
    from inpatient.forms import ReferralForm
    data = _validated_payload(ReferralForm, payload)
    referral = ReferralRecord.objects.create(
        patient=patient,
        source=data.get("source", "Ward"),
        destination=data["destination"],
        reason=data.get("reason", ""),
    )
    return referral, None


# ── Pharmacy handlers ───────────────────────────────────────────────────


def _handle_pharmacy_prescribe(payload, submitted_by):
    from patients.models import Patient
    from pharmacy.models import Drug
    from pharmacy.forms import OfflinePrescribeForm
    from pharmacy.services import prescribe

    data = _validated_payload(OfflinePrescribeForm, payload)
    patient = Patient.objects.get(pk=data["patient_id"])
    drug = Drug.objects.get(pk=data["drug_id"])
    prescribe_data = {
        "dose": data["dose"],
        "route": data["route"],
        "frequency": data["frequency"],
        "duration_days": data.get("duration_days"),
        "safety_override_reason": data.get("safety_override_reason", ""),
        "notes": data.get("notes", ""),
    }
    if data.get("encounter_id"):
        from encounters.models import Encounter
        prescribe_data["encounter"] = Encounter.objects.get(pk=data["encounter_id"])
    prescription, _ = prescribe(patient, drug, submitted_by, prescribe_data)
    return prescription, None


def _handle_pharmacy_approve(payload, submitted_by):
    from pharmacy.forms import OfflineApproveForm
    from pharmacy.models import Prescription
    from pharmacy.services import approve

    data = _validated_payload(OfflineApproveForm, payload)
    prescription = Prescription.objects.get(pk=data["prescription_id"])
    approved = approve(prescription, submitted_by)
    return approved, None


def _handle_pharmacy_dispense(payload, submitted_by):
    from pharmacy.forms import OfflineDispenseForm
    from pharmacy.models import Prescription
    from pharmacy.services import adjust_stock, dispense

    data = _validated_payload(OfflineDispenseForm, payload)
    prescription = Prescription.objects.get(pk=data["prescription_id"])
    dispensed = dispense(prescription, submitted_by, {
        "quantity_dispensed": data["quantity_dispensed"],
        "stock_note": data.get("stock_note", ""),
    })
    adjust_stock(prescription.drug, -1, submitted_by, f"dispensed #{prescription.pk}")
    return dispensed, None


# ── Laboratory handlers ─────────────────────────────────────────────────


def _handle_lab_order(payload, submitted_by):
    from patients.models import Patient
    from laboratory.forms import OfflineLabOrderForm
    from laboratory.services import create_order

    data = _validated_payload(OfflineLabOrderForm, payload)
    patient = Patient.objects.get(pk=data["patient_id"])
    from laboratory.models import LabTest
    test = LabTest.objects.get(pk=data["test_id"])
    encounter = None
    if data.get("encounter_id"):
        from encounters.models import Encounter
        encounter = Encounter.objects.get(pk=data["encounter_id"])
    order = create_order(patient, test, submitted_by, encounter)
    return order, None


def _handle_lab_result(payload, submitted_by):
    from laboratory.forms import OfflineLabResultForm
    from laboratory.models import LabOrder
    from laboratory.services import enter_result

    data = _validated_payload(OfflineLabResultForm, payload)
    order = LabOrder.objects.get(pk=data["order_id"])
    result_data = {k: v for k, v in data.items() if k != "order_id"}
    result = enter_result(order, result_data, submitted_by)
    return result, None


def _handle_lab_verify(payload, submitted_by):
    from laboratory.forms import OfflineLabVerifyForm
    from laboratory.models import LabResult
    from laboratory.services import verify_result

    data = _validated_payload(OfflineLabVerifyForm, payload)
    result = LabResult.objects.get(pk=data["result_id"])
    verified = verify_result(result, submitted_by)
    return verified, None


def _handle_lab_collect(payload, submitted_by):
    from laboratory.forms import OfflineLabCollectForm
    from laboratory.models import LabOrder

    data = _validated_payload(OfflineLabCollectForm, payload)
    order = LabOrder.objects.get(pk=data["order_id"])
    order.mark_collected(submitted_by)
    return order, None


# ── Imaging handlers ────────────────────────────────────────────────────


def _handle_imaging_request(payload, submitted_by):
    from patients.models import Patient
    from imaging.forms import OfflineImagingRequestForm
    from imaging.services import create_request

    data = _validated_payload(OfflineImagingRequestForm, payload)
    patient = Patient.objects.get(pk=data["patient_id"])
    from imaging.models import ImagingModality
    modality = ImagingModality.objects.get(pk=data["modality_id"])
    encounter = None
    if data.get("encounter_id"):
        from encounters.models import Encounter
        encounter = Encounter.objects.get(pk=data["encounter_id"])
    imaging_request = create_request(
        patient=patient,
        modality=modality,
        requested_by=submitted_by,
        clinical_indication=data["clinical_indication"],
        encounter=encounter,
        pregnancy_status_checked=data.get("pregnancy_status_checked", False),
    )
    return imaging_request, None


def _handle_imaging_report(payload, submitted_by):
    from imaging.forms import OfflineImagingReportForm
    from imaging.models import ImagingRequest
    from imaging.services import enter_report

    data = _validated_payload(OfflineImagingReportForm, payload)
    imaging_request = ImagingRequest.objects.get(pk=data["request_id"])
    report_data = {k: v for k, v in data.items() if k != "request_id"}
    report = enter_report(imaging_request, report_data, submitted_by)
    return report, None


# ── Emergency handlers ──────────────────────────────────────────────────


def _handle_triage(payload, submitted_by):
    from patients.models import Patient
    from emergency.forms import OfflineTriageForm
    from emergency.services import triage_patient

    data = _validated_payload(OfflineTriageForm, payload)
    patient = Patient.objects.get(pk=data["patient_id"])
    triage = triage_patient(
        patient=patient,
        triaged_by=submitted_by,
        triage_category=data["triage_category"],
        presenting_condition=data["presenting_condition"],
    )
    # Optionally resolve immediately
    if data.get("outcome"):
        from emergency.services import resolve_triage
        resolve_triage(triage, data["outcome"], data.get("disposition_note", ""))
    return triage, None


def _handle_resolve_triage(payload, submitted_by):
    from emergency.forms import OfflineResolveTriageForm
    from emergency.models import TriageEncounter
    from emergency.services import resolve_triage

    data = _validated_payload(OfflineResolveTriageForm, payload)
    triage = TriageEncounter.objects.get(pk=data["triage_id"])
    resolve_triage(triage, data["outcome"], data.get("disposition_note", ""))
    return triage, None


# ── Dialysis handlers ───────────────────────────────────────────────────


def _handle_dialysis_prescription(payload, submitted_by):
    from patients.models import Patient
    from dialysis.forms import OfflineDialysisPrescriptionForm
    from dialysis.services import prescribe_dialysis

    data = _validated_payload(OfflineDialysisPrescriptionForm, payload)
    patient = Patient.objects.get(pk=data["patient_id"])
    prescription = prescribe_dialysis(
        patient=patient,
        frequency_per_week=data["frequency_per_week"],
        prescribed_by=submitted_by,
        target_fluid_removal_l=data.get("target_fluid_removal_l"),
        vascular_access=data["vascular_access"],
    )
    return prescription, None


def _handle_dialysis_session(payload, submitted_by):
    from dialysis.forms import OfflineDialysisSessionForm
    from dialysis.models import DialysisPrescription
    from dialysis.services import record_session
    from django.utils import timezone

    data = _validated_payload(OfflineDialysisSessionForm, payload)
    prescription = DialysisPrescription.objects.get(pk=data["prescription_id"])
    session_data = {
        "session_date": timezone.now().date(),
        "pre_weight_kg": data["pre_weight_kg"],
        "post_weight_kg": data["post_weight_kg"],
        "complications": data.get("complications", ""),
        "notes": data.get("notes", ""),
    }
    session = record_session(prescription, submitted_by, session_data)
    return session, None


# ── Billing handlers ────────────────────────────────────────────────────


def _handle_invoice_create(payload, submitted_by):
    import json
    from patients.models import Patient
    from billing.forms import OfflineInvoiceCreateForm
    from billing.services import create_invoice, add_line_item
    from billing.models import ServiceCatalogItem

    data = _validated_payload(OfflineInvoiceCreateForm, payload)
    patient = Patient.objects.get(pk=data["patient_id"])
    invoice = create_invoice(patient=patient, created_by=submitted_by, payer_type=data["payer_type"])
    line_items = json.loads(data["line_items"])
    for item in line_items:
        service_item = ServiceCatalogItem.objects.get(pk=item["service_item_id"])
        add_line_item(invoice=invoice, service_item=service_item, quantity=item.get("quantity", 1))
    return invoice, None


def _handle_payment(payload, submitted_by):
    from billing.forms import OfflinePaymentForm
    from billing.models import Invoice
    from billing.services import record_payment

    data = _validated_payload(OfflinePaymentForm, payload)
    invoice = Invoice.objects.get(pk=data["invoice_id"])
    payment = record_payment(
        invoice=invoice,
        amount_mwk=data["amount_mwk"],
        method=data["method"],
        reference=data.get("reference", ""),
        received_by=submitted_by,
    )
    return payment, None


def _handle_task_assign(payload, submitted_by):
    from accounts.models import Task
    from patients.models import Patient
    from django.contrib.auth import get_user_model

    User = get_user_model()
    task = Task.objects.create(
        title=payload["title"],
        description=payload.get("description", ""),
        assigned_to=User.objects.get(pk=payload["assigned_to_id"]),
        assigned_by=submitted_by,
        patient=Patient.objects.get(pk=payload["patient_id"]) if payload.get("patient_id") else None,
        priority=payload.get("priority", "medium"),
        status="pending",
        due_date=payload.get("due_date"),
    )
    return task, None


def _handle_task_update_status(payload, submitted_by):
    from accounts.models import Task

    task = Task.objects.get(pk=payload["task_id"])
    task.status = payload["status"]
    task.save(update_fields=["status"])
    return task, None


HANDLERS = {
    "patient_registration": _handle_patient_registration,
    "encounter_note": _handle_encounter_note,
    "vitals_entry": _handle_vitals_entry,
    "ward_round_note": _handle_ward_round_note,
    "mar_entry": _handle_mar_entry,
    "care_plan_create": _handle_care_plan_create,
    "care_plan_evaluate": _handle_care_plan_evaluate,
    "fluid_balance_entry": _handle_fluid_balance_entry,
    "procedure_note": _handle_procedure_note,
    "nursing_assessment": _handle_nursing_assessment,
    "referral": _handle_referral,
    "pharmacy_prescribe": _handle_pharmacy_prescribe,
    "pharmacy_approve": _handle_pharmacy_approve,
    "pharmacy_dispense": _handle_pharmacy_dispense,
    "lab_order": _handle_lab_order,
    "lab_result": _handle_lab_result,
    "lab_verify": _handle_lab_verify,
    "lab_collect": _handle_lab_collect,
    "imaging_request": _handle_imaging_request,
    "imaging_report": _handle_imaging_report,
    "triage": _handle_triage,
    "resolve_triage": _handle_resolve_triage,
    "dialysis_prescription": _handle_dialysis_prescription,
    "dialysis_session": _handle_dialysis_session,
    "invoice_create": _handle_invoice_create,
    "payment": _handle_payment,
    "task_assign": _handle_task_assign,
    "task_update_status": _handle_task_update_status,
}


def dispatch(form_type, payload, submitted_by):
    handler = HANDLERS.get(form_type)
    if handler is None:
        raise ValueError(f"Unknown form_type: {form_type}")
    return handler(payload, submitted_by)
