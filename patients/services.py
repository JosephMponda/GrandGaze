"""
Public interface for the `patients` app. Other apps must call these
functions, never reach into Patient internals directly (Engineer A spec §3).
"""
from datetime import date

from django.contrib.auth.models import User
from django.contrib.postgres.search import TrigramSimilarity
from django.db import transaction
from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404

from core.encrypted_fields import hash_lookup_value
from .models import DuplicateConfirmation, Patient, PatientNumberSequence

DUPLICATE_MATCH_THRESHOLD = 0.4  # trigram similarity on "first last" name string


def get_patient_or_404(patient_id) -> Patient:
    return get_object_or_404(Patient, pk=patient_id)


def search_patients(query: str) -> QuerySet[Patient]:
    query = (query or "").strip()
    if not query:
        return Patient.objects.none()
    tokens = query.split()
    filters = Q()
    for token in tokens:
        filters |= Q(patient_number__icontains=token) | Q(first_name__icontains=token) | Q(last_name__icontains=token)
    filters |= Q(phone_number_lookup=hash_lookup_value(query))  # encrypted field: exact match only
    return Patient.objects.filter(filters).filter(is_active=True)[:25]


def check_possible_duplicate(data: dict) -> QuerySet[Patient]:
    """Fuzzy match on (first_name, last_name, date_of_birth), or exact
    national_id / phone_number match. Brief §8.1.1 patient safety requirement.
    """
    first_name = data.get("first_name", "")
    last_name = data.get("last_name", "")
    dob = data.get("date_of_birth")

    exact = Patient.objects.filter(is_active=True)
    exact_ids = set()
    if data.get("national_id"):
        exact_ids |= set(exact.filter(national_id_lookup=hash_lookup_value(data["national_id"])).values_list("pk", flat=True))
    if data.get("phone_number"):
        exact_ids |= set(exact.filter(phone_number_lookup=hash_lookup_value(data["phone_number"])).values_list("pk", flat=True))

    fuzzy_ids = set()
    if first_name and last_name:
        candidates = Patient.objects.filter(is_active=True)
        if dob:
            candidates = candidates.filter(date_of_birth=dob)
        fuzzy_ids = set(
            candidates.annotate(
                similarity=TrigramSimilarity("first_name", first_name) + TrigramSimilarity("last_name", last_name)
            )
            .filter(similarity__gt=DUPLICATE_MATCH_THRESHOLD)
            .values_list("pk", flat=True)
        )

    return Patient.objects.filter(pk__in=exact_ids | fuzzy_ids)


def _generate_patient_number() -> str:
    prefix = f"MUST-{date.today().strftime('%Y%m')}-"
    last = Patient.objects.filter(patient_number__startswith=prefix).order_by("-patient_number").first()
    first_seq = int(last.patient_number.split("-")[-1]) + 1 if last else 1
    counter, _created = PatientNumberSequence.objects.select_for_update().get_or_create(
        prefix=prefix,
        defaults={"next_value": first_seq},
    )
    next_seq = max(counter.next_value, first_seq)
    counter.next_value = next_seq + 1
    counter.save(update_fields=["next_value"])
    return f"{prefix}{next_seq:05d}"


@transaction.atomic
def register_patient(data: dict, registered_by: User) -> Patient:
    """Create a Patient. Caller is responsible for having already run
    check_possible_duplicate() and obtained explicit confirmation if needed
    (see confirm_not_duplicate()).
    """
    patient = Patient.objects.create(
        patient_number=_generate_patient_number(),
        registered_by=registered_by,
        **data,
    )
    return patient


@transaction.atomic
def confirm_not_duplicate(new_patient: Patient, candidate: Patient, confirmed_by: User, note: str = "") -> DuplicateConfirmation:
    """Logs the registrar's explicit override of a possible-duplicate warning.
    This is a safety-relevant audit event (Engineer A spec §2), not optional.
    """
    return DuplicateConfirmation.objects.create(
        new_patient=new_patient,
        candidate_patient=candidate,
        confirmed_by=confirmed_by,
        note=note,
    )
