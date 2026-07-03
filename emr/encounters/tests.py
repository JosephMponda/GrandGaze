import pytest
from django.contrib.auth.models import Group, User
from django.urls import reverse

from accounts.models import Profile, Role
from encounters import services
from encounters.models import AllergyRecord, Encounter
from patients import services as patient_services

pytestmark = pytest.mark.django_db


@pytest.fixture
def clinician_user():
    Group.objects.get_or_create(name="Clinician")
    u = User.objects.create_user("clinician1", password="TestPass123!")
    Profile.objects.create(user=u, role=Role.CLINICIAN)
    u.groups.add(Group.objects.get(name="Clinician"))
    return u


@pytest.fixture
def patient(clinician_user):
    return patient_services.register_patient(
        dict(first_name="Grace", last_name="Banda", sex="female"), registered_by=clinician_user
    )


# --- happy path ---

def test_clinician_can_complete_and_sign_encounter(client, clinician_user, patient):
    client.force_login(clinician_user)
    r = client.post(
        reverse("encounters:new", args=[patient.pk]),
        {"encounter_type": "outpatient", "presenting_complaint": "Cough", "diagnosis": "URTI"},
    )
    assert r.status_code == 302
    encounter = Encounter.objects.get(patient=patient)
    assert encounter.presenting_complaint == "Cough"

    r2 = client.post(reverse("encounters:detail", args=[encounter.pk]), {"sign": "1"})
    encounter.refresh_from_db()
    assert encounter.is_signed
    assert encounter.status == "closed"


def test_signed_encounter_is_read_only_addendum_required(client, clinician_user, patient):
    encounter = services.create_encounter(patient, clinician_user, dict(presenting_complaint="Cough"))
    services.sign_encounter(encounter, clinician_user)

    client.force_login(clinician_user)
    # Attempting to edit directly must not change signed content.
    client.post(reverse("encounters:edit", args=[encounter.pk]), {"presenting_complaint": "REWRITTEN"})
    encounter.refresh_from_db()
    assert encounter.presenting_complaint == "Cough"  # unchanged — edit was rejected

    client.post(reverse("encounters:detail", args=[encounter.pk]), {"add_addendum": "1", "note": "Follow-up note"})
    assert encounter.addenda.count() == 1
    assert encounter.addenda.first().note == "Follow-up note"


def test_get_patient_allergies_cross_module_contract(clinician_user, patient):
    """The exact safety contract Pharmacy (Engineer D) depends on."""
    AllergyRecord.objects.create(patient=patient, allergen="Penicillin", severity="severe", recorded_by=clinician_user)
    allergies = services.get_patient_allergies(patient)
    assert allergies.count() == 1
    assert allergies.first().allergen == "Penicillin"


# --- permission-denied path ---

def test_encounter_creation_requires_login(client, patient):
    r = client.post(
        reverse("encounters:new", args=[patient.pk]),
        {"encounter_type": "outpatient", "presenting_complaint": "Cough"},
    )
    assert r.status_code == 302
    assert "/accounts/login/" in r.headers["Location"]


# --- validation-failure path ---

def test_encounter_requires_presenting_complaint(client, clinician_user, patient):
    client.force_login(clinician_user)
    r = client.post(reverse("encounters:new", args=[patient.pk]), {"encounter_type": "outpatient"})
    assert r.status_code == 200  # re-rendered form, not created
    assert Encounter.objects.filter(patient=patient).count() == 0
