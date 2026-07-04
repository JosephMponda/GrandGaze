from django.db import transaction
from django.db.models import QuerySet

from reporting.services import raise_alert

from .models import EarlyWarningScore, VitalSignSet
from .scoring import compute_ews, find_abnormal_values


def latest_vitals(patient) -> VitalSignSet | None:
    return VitalSignSet.objects.filter(patient=patient).order_by("-recorded_at").first()


def vitals_trend(patient, limit=10) -> QuerySet[VitalSignSet]:
    return VitalSignSet.objects.filter(patient=patient).order_by("-recorded_at")[:limit]


@transaction.atomic
def record_vitals(encounter, recorded_by, data: dict) -> VitalSignSet:
    """Create a VitalSignSet, compute BMI (via model.save()) + EWS, and fire
    an alert for any hard-threshold abnormal value - all within the same
    request/response cycle (Engineer B spec §2, no polling delay).
    """
    vitals = VitalSignSet.objects.create(encounter=encounter, patient=encounter.patient, recorded_by=recorded_by, **data)

    score, risk_level = compute_ews(vitals)
    EarlyWarningScore.objects.create(vital_sign_set=vitals, score=score, risk_level=risk_level)

    for message in find_abnormal_values(vitals):
        raise_alert(patient=vitals.patient, source="vitals", severity="critical", message=message)

    return vitals
