from datetime import date

import pytest
from django.contrib.auth.models import Group, User

from accounts.models import Profile, Role
from encounters.models import AllergyRecord, Encounter, Severity
from patients.models import Patient

from . import services
from .models import Drug, DrugAllergyMap, PrescriptionStatus
from .safety import check_prescription_safety

pytestmark = pytest.mark.django_db


@pytest.fixture
def clinician():
    Group.objects.get_or_create(name="Clinician")
    user = User.objects.create_user("clinician_p", password="TestPass123!")
    Profile.objects.create(user=user, role=Role.CLINICIAN)
    user.groups.add(Group.objects.get(name="Clinician"))
    return user


@pytest.fixture
def pharmacist():
    Group.objects.get_or_create(name="Pharmacist")
    user = User.objects.create_user("pharmacist_p", password="TestPass123!")
    Profile.objects.create(user=user, role=Role.PHARMACIST)
    user.groups.add(Group.objects.get(name="Pharmacist"))
    return user


@pytest.fixture
def patient(clinician):
    return Patient.objects.create(
        patient_number="MUST-202607-00003",
        first_name="John",
        last_name="Mvula",
        sex="male",
        date_of_birth=date(2020, 1, 1),
        registered_by=clinician,
    )


def test_allergy_safety_warning_uses_encounter_contract(patient, clinician):
    drug = Drug.objects.create(name="Amoxicillin 250mg", generic_name="Amoxicillin", formulation="capsule")
    DrugAllergyMap.objects.create(drug=drug, allergen_keyword="penicillin")
    AllergyRecord.objects.create(patient=patient, allergen="Penicillin", reaction="rash", severity=Severity.SEVERE, recorded_by=clinician)

    warnings = check_prescription_safety(patient, drug, "250 mg")

    assert [w.code for w in warnings] == ["allergy"]
    assert warnings[0].level == "critical"


def test_prescribe_requires_override_reason_when_warning_present(patient, clinician):
    drug = Drug.objects.create(name="Amoxicillin 250mg", generic_name="Amoxicillin", formulation="capsule")
    DrugAllergyMap.objects.create(drug=drug, allergen_keyword="penicillin")
    AllergyRecord.objects.create(patient=patient, allergen="Penicillin", reaction="rash", severity=Severity.SEVERE, recorded_by=clinician)

    with pytest.raises(ValueError):
        services.prescribe(patient, drug, clinician, {"dose": "250 mg", "route": "oral", "frequency": "TDS"})


def test_pediatric_dose_warning(patient):
    drug = Drug.objects.create(name="Paracetamol syrup", generic_name="Paracetamol", formulation="syrup", pediatric_max_dose_mg=500)

    warnings = check_prescription_safety(patient, drug, "750 mg")

    assert any(w.code == "pediatric_dose" and w.level == "critical" for w in warnings)


def test_duplicate_therapy_warning(patient, clinician):
    drug = Drug.objects.create(name="Ibuprofen", generic_name="Ibuprofen", formulation="tablet")
    services.prescribe(patient, drug, clinician, {"dose": "200 mg", "route": "oral", "frequency": "TDS"})

    warnings = check_prescription_safety(patient, drug, "200 mg")

    assert any(w.code == "duplicate" and w.level == "warning" for w in warnings)


def test_dispensing_changes_status_and_records_actor(patient, clinician, pharmacist):
    drug = Drug.objects.create(name="ORS", generic_name="Oral rehydration salts", formulation="sachet")
    prescription, _ = services.prescribe(patient, drug, clinician, {"dose": "1 sachet", "route": "oral", "frequency": "after each stool"})

    record = services.dispense(prescription, pharmacist, {"quantity_dispensed": "10 sachets", "stock_note": "available"})

    prescription.refresh_from_db()
    assert prescription.status == PrescriptionStatus.DISPENSED
    assert record.dispensed_by == pharmacist
