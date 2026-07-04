from datetime import date

import pytest
from django import forms
from django.contrib.auth.models import Group, User
from django.urls import reverse

from accounts.models import Profile, Role
from encounters.models import AllergyRecord, Encounter, Severity
from patients.models import Patient

from . import services
from .models import Drug, DrugAllergyMap, Prescription, PrescriptionStatus
from .safety import CriticalSafetyBlock, check_prescription_safety

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
    drug = Drug.objects.create(name="Ibuprofen", generic_name="Ibuprofen", formulation="tablet")
    services.prescribe(patient, drug, clinician, {"dose": "200 mg", "route": "oral", "frequency": "TDS"})

    with pytest.raises(ValueError):
        # Second prescription of the same drug within 30 days -> warning-level
        # "duplicate therapy" alert, not critical - missing reason should
        # raise plain ValueError, not CriticalSafetyBlock.
        services.prescribe(patient, drug, clinician, {"dose": "200 mg", "route": "oral", "frequency": "TDS"})


def test_critical_warning_blocks_prescription_even_with_override_reason(patient, clinician):
    """Regression test: a critical-level warning (e.g. a recorded allergy
    conflict) must not be bypassable just by supplying a
    safety_override_reason - that path is for warning-level alerts only.
    Previously the code treated every warning identically, so a free-text
    reason like "ok" would let a documented-allergy prescription through.
    """
    drug = Drug.objects.create(name="Amoxicillin 250mg", generic_name="Amoxicillin", formulation="capsule")
    DrugAllergyMap.objects.create(drug=drug, allergen_keyword="penicillin")
    AllergyRecord.objects.create(patient=patient, allergen="Penicillin", reaction="rash", severity=Severity.SEVERE, recorded_by=clinician)

    with pytest.raises(CriticalSafetyBlock):
        services.prescribe(
            patient,
            drug,
            clinician,
            {"dose": "250 mg", "route": "oral", "frequency": "TDS", "safety_override_reason": "ok, proceeding anyway"},
        )
    assert not Prescription.objects.filter(patient=patient, drug=drug).exists()


def test_warning_level_alert_still_allows_documented_override(patient, clinician):
    """Sanity check the fix didn't over-correct: a warning-level alert
    (duplicate therapy, not critical) should still go through once a reason
    is documented.
    """
    drug = Drug.objects.create(name="Ibuprofen", generic_name="Ibuprofen", formulation="tablet")
    services.prescribe(patient, drug, clinician, {"dose": "200 mg", "route": "oral", "frequency": "TDS"})

    prescription, warnings = services.prescribe(
        patient, drug, clinician, {"dose": "200 mg", "route": "oral", "frequency": "TDS", "safety_override_reason": "clinically appropriate to continue"}
    )
    assert prescription.pk is not None
    assert any(w.code == "duplicate" for w in warnings)


def test_pediatric_dose_warning(patient):
    drug = Drug.objects.create(name="Paracetamol syrup", generic_name="Paracetamol", formulation="syrup", pediatric_max_dose_mg=500)

    warnings = check_prescription_safety(patient, drug, "750 mg")

    assert any(w.code == "pediatric_dose" and w.level == "critical" for w in warnings)


def test_duplicate_therapy_warning(patient, clinician):
    drug = Drug.objects.create(name="Ibuprofen", generic_name="Ibuprofen", formulation="tablet")
    services.prescribe(patient, drug, clinician, {"dose": "200 mg", "route": "oral", "frequency": "TDS"})

    warnings = check_prescription_safety(patient, drug, "200 mg")

    assert any(w.code == "duplicate" and w.level == "warning" for w in warnings)


def test_notes_field_rendered_in_prescribe_form(client, patient, clinician):
    """C1: the notes field must appear and accept input."""
    client.force_login(clinician)
    response = client.get(reverse("pharmacy:prescribe", args=[patient.pk]))
    assert 'name="notes"' in response.content.decode()


def test_encounter_field_rendered_in_prescribe_form(client, patient, clinician):
    """H6: form has encounter field, queryset is filtered, template must render it."""
    client.force_login(clinician)
    response = client.get(reverse("pharmacy:prescribe", args=[patient.pk]))
    assert 'name="encounter"' in response.content.decode()


def test_proceed_with_warnings_is_checkbox_not_hidden(patient, clinician):
    """H4: proceed_with_warnings widget must be a visible CheckboxInput."""
    from pharmacy.forms import PrescriptionForm
    form = PrescriptionForm()
    widget = form.fields["proceed_with_warnings"].widget
    assert isinstance(widget, forms.CheckboxInput)


def test_dispensing_changes_status_and_records_actor(patient, clinician, pharmacist):
    drug = Drug.objects.create(name="ORS", generic_name="Oral rehydration salts", formulation="sachet")
    prescription, _ = services.prescribe(patient, drug, clinician, {"dose": "1 sachet", "route": "oral", "frequency": "after each stool"})

    record = services.dispense(prescription, pharmacist, {"quantity_dispensed": "10 sachets", "stock_note": "available"})

    prescription.refresh_from_db()
    assert prescription.status == PrescriptionStatus.DISPENSED
    assert record.dispensed_by == pharmacist


def test_prescribe_view_blocks_critical_warning_even_with_override_checked(client, patient, clinician):
    """Same regression as the services-layer test, but through the actual
    HTTP view - this is where the bug originally shipped (the view computed
    critical vs. warning level but never branched on it).
    """
    drug = Drug.objects.create(name="Amoxicillin 250mg", generic_name="Amoxicillin", formulation="capsule")
    DrugAllergyMap.objects.create(drug=drug, allergen_keyword="penicillin")
    AllergyRecord.objects.create(patient=patient, allergen="Penicillin", reaction="rash", severity=Severity.SEVERE, recorded_by=clinician)

    client.force_login(clinician)
    response = client.post(
        reverse("pharmacy:prescribe", args=[patient.pk]),
        {
            "drug": drug.pk,
            "dose": "250 mg",
            "route": "oral",
            "frequency": "TDS",
            "proceed_with_warnings": "on",
            "safety_override_reason": "ok, proceeding anyway",
        },
    )
    assert response.status_code == 200  # re-rendered, blocked - never redirects to the queue
    assert response.context["blocked"] is True
    assert not Prescription.objects.filter(patient=patient, drug=drug).exists()
