from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from .models import CATEGORY_ORDER, TriageEncounter


def triage_patient(patient, triaged_by, triage_category, presenting_condition) -> TriageEncounter:
    return TriageEncounter.objects.create(
        patient=patient,
        triaged_by=triaged_by,
        triage_category=triage_category,
        presenting_condition=presenting_condition,
    )


def resolve_triage(triage: TriageEncounter, outcome: str, note: str = "") -> TriageEncounter:
    triage.outcome = outcome
    triage.disposition_note = note
    from django.utils import timezone
    triage.resolved_at = timezone.now()
    triage.save(update_fields=["outcome", "disposition_note", "resolved_at"])
    return triage


def triage_queue() -> QuerySet[TriageEncounter]:
    """Active triages sorted by severity (most urgent first)."""
    qs = TriageEncounter.objects.filter(outcome__isnull=True).select_related("patient", "triaged_by")
    sorted_qs = sorted(qs, key=lambda t: CATEGORY_ORDER.get(t.triage_category, 99))
    return sorted_qs


def active_triages_for(patient) -> QuerySet[TriageEncounter]:
    return TriageEncounter.objects.filter(patient=patient, outcome__isnull=True).select_related("triaged_by")


def triage_history_for(patient, limit=10) -> list[TriageEncounter]:
    return list(TriageEncounter.objects.filter(patient=patient).select_related("triaged_by")[:limit])
