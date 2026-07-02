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
from .models import DuplicateConfirmation, Patient

DUPLICATE_MATCH_THRESHOLD = 0.4  # trigram similarity on "first last" name string


def get_patient_or_404(patient_id) -> Patient:
    return get_object_or_404(Patient, pk=patient_id)


def search_patients(query: str) -> QuerySet[Patient]:
    query = (query or "").strip()
    if not query:
        return Patient.objects.none()
    filters = Q(patient_number__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query)
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
    exact_matches = Patient.objects.none()
    if data.get("national_id"):
        exact_matches = exact_matches | exact.filter(national_id_lookup=hash_lookup_value(data["national_id"]))
    if data.get("phone_number"):
        exact_matches = exact_matches | exact.filter(phone_number_lookup=hash_lookup_value(data["phone_number"]))

    fuzzy_matches = Patient.objects.none()
    if first_name and last_name:
        full_name = f"{first_name} {last_name}"
        candidates = Patient.objects.filter(is_active=True)
        if dob:
            candidates = candidates.filter(date_of_birth=dob)
        fuzzy_matches = (
            candidates.annotate(
                similarity=TrigramSimilarity("first_name", first_name) + TrigramSimilarity("last_name", last_name)
            )
            .filter(similarity__gt=DUPLICATE_MATCH_THRESHOLD)
            .order_by("-similarity")
        )

    return (exact_matches | fuzzy_matches).distinct()[:10]


def _generate_patient_number() -> str:
    prefix = f"MUST-{date.today().strftime('%Y%m')}-"
    last = Patient.objects.filter(patient_number__startswith=prefix).order_by("-patient_number").first()
    next_seq = int(last.patient_number.split("-")[-1]) + 1 if last else 1
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
