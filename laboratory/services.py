from django.db.models import Avg, DurationField, ExpressionWrapper, F, QuerySet
from django.utils import timezone

from .models import LabOrder, LabOrderStatus, LabResult, LabTest


def create_order(patient, test: LabTest, ordered_by, encounter=None) -> LabOrder:
    return LabOrder.objects.create(patient=patient, encounter=encounter, test=test, ordered_by=ordered_by)


def enter_result(order: LabOrder, data: dict, entered_by) -> LabResult:
    result, _ = LabResult.objects.update_or_create(order=order, defaults={**data, "entered_by": entered_by})
    return result


def verify_result(result: LabResult, verified_by) -> LabResult:
    if result.entered_by_id == verified_by.id:
        raise ValueError("The result verifier must be different from the result entry user.")
    result.verified_by = verified_by
    result.verified_at = timezone.now()
    result.save(update_fields=["verified_by", "verified_at", "is_abnormal", "is_critical"])
    return result


def pending_orders_for(patient) -> QuerySet[LabOrder]:
    return LabOrder.objects.filter(patient=patient).exclude(status__in=[LabOrderStatus.VERIFIED, LabOrderStatus.CANCELLED])


def recent_results_for(patient, limit=10) -> QuerySet[LabResult]:
    return LabResult.objects.filter(order__patient=patient).select_related("order", "order__test")[:limit]


def workload_summary() -> dict:
    pending = LabOrder.objects.exclude(status__in=[LabOrderStatus.VERIFIED, LabOrderStatus.CANCELLED]).count()
    resulted = LabOrder.objects.filter(status__in=[LabOrderStatus.RESULTED, LabOrderStatus.VERIFIED]).count()
    avg_turnaround = (
        LabResult.objects.annotate(turnaround=ExpressionWrapper(F("entered_at") - F("order__created_at"), output_field=DurationField()))
        .aggregate(value=Avg("turnaround"))
        .get("value")
    )
    return {"pending": pending, "resulted": resulted, "avg_turnaround": avg_turnaround}

