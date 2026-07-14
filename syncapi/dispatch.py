"""Dispatch table mapping form_type -> handler function.

Each handler receives (payload_json, submitted_by) and returns
(record_or_none, conflict_description_or_none).
"""

from django.db import transaction

from encounters.forms import EncounterForm
from vitals.forms import VitalSignSetForm

from patients.services import check_possible_duplicate, confirm_not_duplicate, register_patient
from patients.forms import PatientRegistrationForm


def _validated_payload(form_class, payload):
    """Apply the same ModelForm validation used by online clinical workflows."""
    form = form_class(payload)
    if not form.is_valid():
        raise ValueError(form.errors.get_json_data())
    return form.cleaned_data


def _handle_patient_registration(payload, submitted_by):
    # Same safety gate as the online registration view (patients/views.py) -
    # register_patient() itself does NOT run this check, so every caller
    # must. Skipping it here would let offline-synced registrations bypass
    # duplicate-patient detection entirely.
    confirmed_id = payload.get("confirmed_not_duplicate_of")
    patient_data = _validated_payload(PatientRegistrationForm, payload)
    duplicates = check_possible_duplicate(patient_data)
    confirmed = duplicates.filter(pk=confirmed_id).first() if confirmed_id else None
    remaining = duplicates.exclude(pk=confirmed.pk) if confirmed else duplicates
    if remaining.exists() or (confirmed_id and not confirmed):
        candidates = ", ".join(p.patient_number for p in remaining[:5])
        return None, f"Possible duplicate patient(s): {candidates}. Confirm on next sync."

    patient = register_patient(patient_data, registered_by=submitted_by)
    if confirmed:
        confirm_not_duplicate(patient, confirmed, confirmed_by=submitted_by)
    return patient, None


def _handle_encounter_note(payload, submitted_by):
    from encounters.services import create_encounter
    from patients.models import Patient

    patient = Patient.objects.get(pk=payload["patient_id"])
    encounter = create_encounter(patient=patient, clinician=submitted_by, data=_validated_payload(EncounterForm, payload))
    return encounter, None


def _handle_vitals_entry(payload, submitted_by):
    from encounters.models import Encounter
    from vitals.services import record_vitals

    encounter = Encounter.objects.get(pk=payload["encounter_id"])
    if encounter.signed_at:
        return None, f"Encounter #{encounter.pk} is already signed; cannot add vitals."
    vitals = record_vitals(encounter=encounter, recorded_by=submitted_by, data=_validated_payload(VitalSignSetForm, payload))
    return vitals, None


HANDLERS = {
    "patient_registration": _handle_patient_registration,
    "encounter_note": _handle_encounter_note,
    "vitals_entry": _handle_vitals_entry,
}


def dispatch(form_type, payload, submitted_by):
    handler = HANDLERS.get(form_type)
    if handler is None:
        raise ValueError(f"Unknown form_type: {form_type}")
    return handler(payload, submitted_by)
