from django.db.models import QuerySet

from .models import ImagingReport, ImagingRequest, ImagingStatus


def create_request(patient, modality, requested_by, clinical_indication, encounter=None, pregnancy_status_checked=False, scheduled_at=None):
    return ImagingRequest.objects.create(
        patient=patient,
        encounter=encounter,
        modality=modality,
        requested_by=requested_by,
        clinical_indication=clinical_indication,
        pregnancy_status_checked=pregnancy_status_checked,
        scheduled_at=scheduled_at,
        status=ImagingStatus.SCHEDULED if scheduled_at else ImagingStatus.REQUESTED,
    )


def enter_report(request: ImagingRequest, data: dict, reported_by) -> ImagingReport:
    report, _ = ImagingReport.objects.update_or_create(request=request, defaults={**data, "reported_by": reported_by})
    return report


def pending_requests_for(patient) -> QuerySet[ImagingRequest]:
    return ImagingRequest.objects.filter(patient=patient).exclude(status=ImagingStatus.REPORTED)


def recent_reports_for(patient, limit=10) -> QuerySet[ImagingReport]:
    return ImagingReport.objects.filter(request__patient=patient).select_related("request", "request__modality")[:limit]

