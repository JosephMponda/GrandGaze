"""Dispatch table mapping form_type -> handler function.

Each handler receives (payload_json, submitted_by) and returns
(record_or_none, conflict_description_or_none).
"""

from django.db import transaction

from patients.services import register_patient


def _handle_patient_registration(payload, submitted_by):
    patient = register_patient(payload, registered_by=submitted_by)
    return patient, None


def _handle_encounter_note(payload, submitted_by):
    from encounters.services import create_encounter
    from patients.models import Patient

    patient = Patient.objects.get(pk=payload["patient_id"])
    encounter = create_encounter(patient=patient, clinician=submitted_by, data=payload)
    return encounter, None


def _handle_vitals_entry(payload, submitted_by):
    from encounters.models import Encounter
    from vitals.services import record_vitals

    encounter = Encounter.objects.get(pk=payload["encounter_id"])
    if encounter.signed_at:
        return None, f"Encounter #{encounter.pk} is already signed; cannot add vitals."
    vitals = record_vitals(encounter=encounter, recorded_by=submitted_by, data=payload)
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
