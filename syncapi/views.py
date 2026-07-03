from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .dispatch import dispatch
from .models import SyncConflict, SyncSubmission
from .serializers import SyncStatusSerializer, SyncSubmitSerializer


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
            return Response({"status": "already_applied", "submission_id": existing.pk})
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

    submission.status = SyncSubmission.Status.APPLIED
    submission.applied_at = timezone.now()
    submission.save(update_fields=["status", "applied_at"])
    return Response({"status": "applied", "submission_id": submission.pk})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sync_status(request):
    submissions = SyncSubmission.objects.filter(submitted_by=request.user).order_by("-received_at")[:50]
    serializer = SyncStatusSerializer(submissions, many=True)
    return Response(serializer.data)
