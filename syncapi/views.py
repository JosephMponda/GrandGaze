from django.db import models
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from patients.models import Patient
from inpatient.models import Ward, Bed
from pharmacy.models import Drug
from laboratory.models import LabTest
from imaging.models import ImagingModality
from billing.models import ServiceCatalogItem
from emergency.models import TriageEncounter
from dialysis.models import DialysisPrescription, DialysisSession
from accounts.models import Task

from .dispatch import dispatch
from .models import SyncConflict, SyncSubmission
from .serializers import SyncStatusSerializer, SyncSubmitSerializer


def _result_payload(result):
    """Stable server identifiers returned to the local-first client."""
    if result is None:
        return {}
    if hasattr(result, "patient_number"):
        return {"patient_id": result.pk, "patient_number": result.patient_number}
    if hasattr(result, "encounter_id") and hasattr(result, "patient_id") and hasattr(result, "recorded_at"):
        return {"vitals_id": result.pk, "encounter_id": result.encounter_id, "patient_id": result.patient_id}
    if hasattr(result, "test") and hasattr(result, "patient_id"):
        # LabOrder
        return {"order_id": result.pk, "patient_id": result.patient_id}
    if hasattr(result, "order_id") and hasattr(result, "entered_by_id"):
        # LabResult
        return {"result_id": result.pk, "order_id": result.order_id}
    if hasattr(result, "patient_id") and hasattr(result, "encounter"):
        return {"encounter_id": result.pk, "patient_id": result.patient_id}
    return {"record_id": result.pk}


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def sync_submit(request):
    serializer = SyncSubmitSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    client_uuid = serializer.validated_data["client_uuid"]
    existing = SyncSubmission.objects.filter(client_uuid=client_uuid).first()
    if existing:
        if existing.status == SyncSubmission.Status.APPLIED:
            return Response({"status": "already_applied", "submission_id": existing.pk, "result": existing.result_json})
        return Response({"status": existing.status, "submission_id": existing.pk})

    submission = SyncSubmission.objects.create(
        client_uuid=client_uuid,
        form_type=serializer.validated_data["form_type"],
        payload_json=serializer.validated_data["payload_json"],
        submitted_by=request.user,
    )

    try:
        result, conflict_note = dispatch(submission.form_type, submission.payload_json, request.user)
    except Exception as e:
        submission.status = SyncSubmission.Status.REJECTED
        submission.conflict_note = str(e)
        submission.save(update_fields=["status", "conflict_note"])
        return Response({"status": "rejected", "error": str(e)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    if conflict_note:
        submission.status = SyncSubmission.Status.CONFLICT
        submission.conflict_note = conflict_note
        submission.save(update_fields=["status", "conflict_note"])
        SyncConflict.objects.create(submission=submission, conflicting_record_description=conflict_note)
        return Response({"status": "conflict", "conflict_note": conflict_note})

    result_json = _result_payload(result)
    submission.patient_id = result_json.get("patient_id")
    submission.result_json = result_json
    submission.status = SyncSubmission.Status.APPLIED
    submission.applied_at = timezone.now()
    submission.save(update_fields=["patient", "result_json", "status", "applied_at"])
    return Response({"status": "applied", "submission_id": submission.pk, "result": result_json})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def offline_bootstrap(request):
    """Initial local replica for the offline clinical workspace.

    This project currently has no ward/clinician assignment model to limit the
    data set, so it mirrors active patients visible to the logged-in user.
    """
    patients = Patient.objects.filter(is_active=True).order_by("last_name", "first_name")

    # Inpatient reference data
    from inpatient.models import Admission, AdmissionStatus
    from pharmacy.models import Prescription, PrescriptionStatus

    wards = [
        {"server_id": w.pk, "name": w.name, "department": w.department, "bed_count": w.bed_count}
        for w in Ward.objects.all()
    ]
    beds = [
        {"server_id": b.pk, "ward_id": b.ward_id, "label": b.label, "is_occupied": b.is_occupied}
        for b in Bed.objects.select_related("ward").all()
    ]
    active_admissions = Admission.objects.filter(status=AdmissionStatus.ACTIVE).select_related("patient", "bed__ward")
    admissions = [
        {
            "server_id": a.pk,
            "patient_id": a.patient_id,
            "admission_diagnosis": a.admission_diagnosis,
            "bed_id": a.bed_id,
            "ward_name": a.bed.ward.name if a.bed else "",
            "bed_label": a.bed.label if a.bed else "",
            "admitted_at": a.admitted_at.isoformat(),
        }
        for a in active_admissions
    ]
    # Active prescriptions needed for MAR entry
    prescription_ids = set(active_admissions.values_list("patient_id", flat=True))
    prescriptions = [
        {
            "server_id": p.pk,
            "patient_id": p.patient_id,
            "drug_name": p.drug.name if p.drug else "",
            "dose": p.dose,
            "route": p.route,
            "frequency": p.frequency,
        }
        for p in Prescription.objects.filter(
            patient_id__in=prescription_ids,
            status__in=[PrescriptionStatus.PRESCRIBED, PrescriptionStatus.APPROVED, PrescriptionStatus.DISPENSED],
        ).select_related("drug")
    ]

    # Drug catalog for offline prescribing
    drugs = [
        {
            "server_id": d.pk,
            "name": d.name,
            "generic_name": d.generic_name,
            "formulation": d.formulation,
            "is_controlled": d.is_controlled,
        }
        for d in Drug.objects.all()
    ]

    # Lab test catalog for offline ordering
    lab_tests = [
        {
            "server_id": t.pk,
            "name": t.name,
            "loinc_code": t.loinc_code,
            "specimen_type": t.specimen_type,
            "normal_range_low": float(t.normal_range_low) if t.normal_range_low is not None else None,
            "normal_range_high": float(t.normal_range_high) if t.normal_range_high is not None else None,
            "unit": t.unit,
            "is_critical_if_outside_range": t.is_critical_if_outside_range,
        }
        for t in LabTest.objects.all()
    ]

    # Imaging modality catalog for offline ordering
    imaging_modalities = [
        {
            "server_id": m.pk,
            "name": m.name,
            "requires_pregnancy_check": m.requires_pregnancy_check,
            "is_mvp_supported": m.is_mvp_supported,
        }
        for m in ImagingModality.objects.all()
    ]

    # Tasks for the offline user
    tasks = [
        {
            "server_id": t.pk,
            "title": t.title,
            "description": t.description,
            "assigned_to_id": t.assigned_to_id,
            "assigned_by_id": t.assigned_by_id,
            "assigned_to_name": t.assigned_to.get_full_name() or t.assigned_to.username,
            "assigned_by_name": t.assigned_by.get_full_name() or t.assigned_by.username,
            "patient_id": t.patient_id,
            "patient_name": str(t.patient) if t.patient else "",
            "priority": t.priority,
            "status": t.status,
            "due_date": t.due_date.isoformat(),
            "created_at": t.created_at.isoformat(),
        }
        for t in Task.objects.filter(
            models.Q(assigned_to=request.user) | models.Q(assigned_by=request.user)
        ).select_related("assigned_to", "assigned_by", "patient")
    ]

    # Service catalog for offline billing
    service_catalog = [
        {
            "server_id": s.pk,
            "name": s.name,
            "code": s.code,
            "price_mwk": float(s.price_mwk),
        }
        for s in ServiceCatalogItem.objects.all()
    ]

    # Triage encounters (active/unresolved only)
    triage_encounters = [
        {
            "server_id": t.pk,
            "patient_id": t.patient_id,
            "triage_category": t.triage_category,
            "presenting_condition": t.presenting_condition,
            "outcome": t.outcome,
            "disposition_note": t.disposition_note,
            "created_at": t.created_at.isoformat(),
        }
        for t in TriageEncounter.objects.select_related("patient").all()
    ]

    # Active dialysis prescriptions and their sessions
    dialysis_prescriptions = [
        {
            "server_id": p.pk,
            "patient_id": p.patient_id,
            "frequency_per_week": p.frequency_per_week,
            "vascular_access": p.vascular_access,
            "target_fluid_removal_l": float(p.target_fluid_removal_l) if p.target_fluid_removal_l else None,
            "is_active": p.is_active,
            "created_at": p.created_at.isoformat(),
        }
        for p in DialysisPrescription.objects.filter(is_active=True).select_related("patient")
    ]
    dialysis_sessions = [
        {
            "server_id": s.pk,
            "prescription_id": s.prescription_id,
            "pre_weight_kg": float(s.pre_weight_kg),
            "post_weight_kg": float(s.post_weight_kg),
            "complications": s.complications or "",
            "notes": s.notes or "",
            "created_at": s.created_at.isoformat(),
        }
        for s in DialysisSession.objects.select_related("prescription").all()
    ]

    role = "superuser" if request.user.is_superuser else (request.user.profile.role if hasattr(request.user, "profile") and request.user.profile else "")

    return Response(
        {
            "generated_at": timezone.now().isoformat(),
            "user_role": role,
            "user_name": request.user.get_full_name() or request.user.username,
            "tasks": tasks,
            "patients": [
                {
                    "server_id": patient.pk,
                    "patient_number": patient.patient_number,
                    "first_name": patient.first_name,
                    "last_name": patient.last_name,
                    "other_names": patient.other_names,
                    "sex": patient.sex,
                    "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else "",
                    "phone_number": patient.phone_number,
                }
                for patient in patients
            ],
            "wards": wards,
            "beds": beds,
            "admissions": admissions,
            "prescriptions": prescriptions,
            "drugs": drugs,
            "lab_tests": lab_tests,
            "imaging_modalities": imaging_modalities,
            "service_catalog": service_catalog,
            "triage_encounters": triage_encounters,
            "dialysis_prescriptions": dialysis_prescriptions,
            "dialysis_sessions": dialysis_sessions,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sync_status(request):
    submissions = SyncSubmission.objects.filter(submitted_by=request.user).order_by("-received_at")[:50]
    serializer = SyncStatusSerializer(submissions, many=True)
    return Response(serializer.data)
