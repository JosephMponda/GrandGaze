"""Public interface for the dialysis app."""
from datetime import date, timedelta

from django.db.models import Q, QuerySet

from .models import CKDDiagnosis, DialysisPrescription, DialysisSession


def record_ckd_diagnosis(patient, stage, diagnosed_by, notes="") -> CKDDiagnosis:
    return CKDDiagnosis.objects.create(
        patient=patient, stage=stage, diagnosed_by=diagnosed_by, notes=notes
    )


def prescribe_dialysis(
    patient, frequency_per_week, prescribed_by, target_fluid_removal_l=None, vascular_access="av_fistula"
) -> DialysisPrescription:
    return DialysisPrescription.objects.create(
        patient=patient,
        frequency_per_week=frequency_per_week,
        target_fluid_removal_l=target_fluid_removal_l,
        vascular_access=vascular_access,
        prescribed_by=prescribed_by,
    )


def record_session(prescription, conducted_by, data) -> DialysisSession:
    return DialysisSession.objects.create(prescription=prescription, conducted_by=conducted_by, **data)


def active_prescriptions_for(patient) -> QuerySet[DialysisPrescription]:
    return DialysisPrescription.objects.filter(patient=patient, is_active=True)


def missed_sessions(prescription: DialysisPrescription, grace_days: int = 1) -> list[date]:
    """Returns dates where a session was expected but not recorded.

    ponytail: naive heuristic — checks if any session exists per expected
    day this week. Doesn't track rolling schedules or missed-yet-made-up.
    Good enough for a dashboard flag.
    """
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    expected = []
    for i in range(min(prescription.frequency_per_week, 7)):
        day = week_start + timedelta(days=i)
        if day <= today:
            expected.append(day)
    recorded = set(
        prescription.sessions.filter(session_date__in=expected).values_list("session_date", flat=True)
    )
    return [d for d in expected if d not in recorded]


def recent_diagnosis(patient) -> CKDDiagnosis | None:
    return CKDDiagnosis.objects.filter(patient=patient).order_by("-diagnosed_at").first()
