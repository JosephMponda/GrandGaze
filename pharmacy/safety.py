from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import re

from django.db.models import Q
from django.utils import timezone

from encounters.services import get_patient_allergies
from vitals.models import PregnancyStatus
from vitals.services import latest_vitals

from .models import Drug, DrugAllergyMap, Prescription, PrescriptionStatus


@dataclass(frozen=True)
class SafetyWarning:
    level: str
    code: str
    message: str


class CriticalSafetyBlock(Exception):
    """Raised when check_prescription_safety() returns a critical-level
    warning. Unlike warning-level alerts, critical warnings (allergy
    conflict, pediatric dose exceeded) cannot be bypassed with an override
    reason - per AGENTS.md/COMPLETED_FEATURES.md §9.2: "critical blocks
    submit." Carries the full warning list so callers can display why.
    """

    def __init__(self, message: str, warnings: list[SafetyWarning]):
        super().__init__(message)
        self.warnings = warnings


def check_prescription_safety(patient, drug, dose=None) -> list[SafetyWarning]:
    warnings = []
    warnings.extend(_check_allergy(patient, drug))
    warnings.extend(_check_drug_interaction(patient, drug))
    warnings.extend(_check_duplicate_therapy(patient, drug))
    warnings.extend(_check_pregnancy_renal_breastfeeding(patient, drug))
    warnings.extend(_check_pediatric_dose(patient, drug, dose))
    return warnings


def _check_allergy(patient, drug):
    allergies = [a.allergen.lower() for a in get_patient_allergies(patient)]
    if not allergies:
        return []
    keywords = DrugAllergyMap.objects.filter(drug=drug).values_list("allergen_keyword", flat=True)
    for keyword in keywords:
        if any(keyword.lower() in allergen for allergen in allergies):
            return [SafetyWarning("critical", "allergy", f"Recorded allergy may conflict with {drug.generic_name}: {keyword}.")]
    return []


def _check_duplicate_therapy(patient, drug):
    since = timezone.now() - timedelta(days=30)
    exists = Prescription.objects.filter(
        patient=patient,
        created_at__gte=since,
        status__in=[PrescriptionStatus.PRESCRIBED, PrescriptionStatus.APPROVED, PrescriptionStatus.DISPENSED],
    ).filter(drug__generic_name__iexact=drug.generic_name).exists()
    if exists:
        return [SafetyWarning("warning", "duplicate", f"Active recent prescription already exists for {drug.generic_name}.")]
    return []


def _check_drug_interaction(patient, drug):
    active_ids = Prescription.objects.filter(
        patient=patient,
        status__in=[PrescriptionStatus.PRESCRIBED, PrescriptionStatus.APPROVED, PrescriptionStatus.DISPENSED],
    ).exclude(drug=drug).values_list("drug_id", flat=True)
    interacting = drug.interacting_drugs.filter(pk__in=active_ids)
    # ponytail: symmetrical M2M - Django auto-manages both sides
    return [SafetyWarning("critical", "drug_interaction", f"Interaction: {drug.generic_name} may interact with an active prescription.") for _ in interacting]


def _check_pregnancy_renal_breastfeeding(patient, drug):
    warnings = []
    vitals = latest_vitals(patient)
    if drug.contraindicated_in_pregnancy and vitals and vitals.pregnancy_status == PregnancyStatus.PREGNANT:
        warnings.append(SafetyWarning("warning", "pregnancy", f"{drug.generic_name} is flagged as contraindicated in pregnancy."))
    if drug.contraindicated_in_breastfeeding and patient.sex == "female":
        warnings.append(SafetyWarning("warning", "breastfeeding", f"{drug.generic_name} is flagged for caution during breastfeeding."))
    renal_text = " ".join(patient.encounters.values_list("diagnosis", flat=True)[:5]).lower()
    if drug.contraindicated_in_renal and any(term in renal_text for term in ["renal", "kidney", "ckd"]):
        warnings.append(SafetyWarning("warning", "renal", f"{drug.generic_name} is flagged for renal-condition caution."))
    return warnings


def _check_pediatric_dose(patient, drug, dose):
    if drug.pediatric_max_dose_mg is None:
        return []
    if not patient.date_of_birth:
        # ponytail: common Malawi scenario - DOB unknown, warn transparently
        return [SafetyWarning("warning", "pediatric_dose", f"Patient age unknown - pediatric dose check for {drug.generic_name} cannot be verified.")]
    today = date.today()
    age = today.year - patient.date_of_birth.year - ((today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day))
    if age >= 12:
        return []
    parsed = _parse_mg(dose or "")
    if parsed is not None and parsed > drug.pediatric_max_dose_mg:
        return [SafetyWarning("critical", "pediatric_dose", f"Dose exceeds pediatric maximum of {drug.pediatric_max_dose_mg:g} mg.")]
    return []


def _parse_mg(value):
    match = re.search(r"(\d+(?:\.\d+)?)\s*mg\b", str(value).lower())
    if not match:
        return None
    try:
        return Decimal(match.group(1))
    except InvalidOperation:
        return None

