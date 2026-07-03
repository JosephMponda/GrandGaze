from django.db.models import QuerySet
from django.utils import timezone

from .models import AllergyRecord, Encounter


def get_open_encounter(patient) -> Encounter | None:
    return Encounter.objects.filter(patient=patient, status="open").order_by("-created_at").first()


def create_encounter(patient, clinician, data: dict) -> Encounter:
    return Encounter.objects.create(patient=patient, clinician=clinician, **data)


def sign_encounter(encounter: Encounter, clinician) -> Encounter:
    encounter.signed_by = clinician
    encounter.signed_at = timezone.now()
    encounter.status = "closed"
    encounter.save(update_fields=["signed_by", "signed_at", "status", "updated_at"])
    return encounter


def get_patient_allergies(patient) -> QuerySet[AllergyRecord]:
    """The cross-module safety contract — Pharmacy (Engineer D) calls this
    at prescribing time. Patient-level, not encounter-level (Engineer B spec §1).
    """
    return AllergyRecord.objects.filter(patient=patient)
