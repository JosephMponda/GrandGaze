from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .dispatch import dispatch
from .models import SyncConflict, SyncSubmission
from .serializers import SyncStatusSerializer, SyncSubmitSerializer


def _result_payload(result):
    """Stable server identifiers returned to the local-first client."""
    if result is None:
        return {}
    if hasattr(result, "patient_number"):
        return {"patient_id": result.pk, "patient_number": result.patient_number}
    if hasattr(result, "encounter_id"):
        return {"vitals_id": result.pk, "encounter_id": result.encounter_id, "patient_id": result.patient_id}
    if hasattr(result, "patient_id"):
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
    from patients.models import Patient

    patients = Patient.objects.filter(is_active=True).order_by("last_name", "first_name")
    return Response(
        {
            "generated_at": timezone.now().isoformat(),
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
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sync_status(request):
    submissions = SyncSubmission.objects.filter(submitted_by=request.user).order_by("-received_at")[:50]
    serializer = SyncStatusSerializer(submissions, many=True)
    return Response(serializer.data)
