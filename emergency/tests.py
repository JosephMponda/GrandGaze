import pytest
from django.contrib.auth.models import Group, User
from django.urls import reverse

from accounts.models import Profile, Role
from patients.models import Patient

from . import services
from .forms import RapidRegisterForm, TriageForm
from .models import TriageCategory, TriageEncounter

pytestmark = pytest.mark.django_db


@pytest.fixture
def nurse():
    Group.objects.get_or_create(name="Nurse")
    user = User.objects.create_user("nurse_e", password="TestPass123!")
    Profile.objects.create(user=user, role=Role.NURSE)
    user.groups.add(Group.objects.get(name="Nurse"))
    return user


@pytest.fixture
def clinician():
    Group.objects.get_or_create(name="Clinician")
    user = User.objects.create_user("clinician_e", password="TestPass123!")
    Profile.objects.create(user=user, role=Role.CLINICIAN)
    user.groups.add(Group.objects.get(name="Clinician"))
    return user


@pytest.fixture
def patient(nurse):
    return Patient.objects.create(
        patient_number="MUST-202607-00010",
        first_name="Ruth",
        last_name="Banda",
        sex="female",
        registered_by=nurse,
    )


# --- services ---

def test_triage_patient_creates_encounter(patient, nurse):
    t = services.triage_patient(
        patient, nurse, TriageCategory.URGENT, "Severe abdominal pain"
    )
    assert t.pk is not None
    assert t.triage_category == TriageCategory.URGENT
    assert t.presenting_condition == "Severe abdominal pain"
    assert t.triaged_by == nurse
    assert t.patient == patient
    assert t.outcome is None
    assert t.rapid_registration is False


def test_resolve_triage_sets_outcome(patient, nurse):
    t = services.triage_patient(patient, nurse, TriageCategory.IMMEDIATE, "Unconscious")
    services.resolve_triage(t, "admitted", "Transferred to ICU")
    t.refresh_from_db()
    assert t.outcome == "admitted"
    assert t.disposition_note == "Transferred to ICU"
    assert t.resolved_at is not None


def test_triage_queue_orders_by_severity(patient, clinician, nurse):
    services.triage_patient(patient, nurse, TriageCategory.STANDARD, "Mild fever")
    p2 = Patient.objects.create(patient_number="MUST-202607-00011", first_name="James", last_name="Chiwa", sex="male", registered_by=nurse)
    services.triage_patient(p2, clinician, TriageCategory.IMMEDIATE, "Cardiac arrest")
    p3 = Patient.objects.create(patient_number="MUST-202607-00012", first_name="Alice", last_name="Kamanga", sex="female", registered_by=nurse)
    services.triage_patient(p3, nurse, TriageCategory.URGENT, "Severe dehydration")

    queue = services.triage_queue()
    assert len(queue) == 3
    assert queue[0].triage_category == TriageCategory.IMMEDIATE
    assert queue[1].triage_category == TriageCategory.URGENT
    assert queue[2].triage_category == TriageCategory.STANDARD


def test_resolved_triage_not_in_queue(patient, nurse):
    t = services.triage_patient(patient, nurse, TriageCategory.URGENT, "Fever")
    services.resolve_triage(t, "discharged")
    assert len(services.triage_queue()) == 0


# --- forms ---

def test_triage_form_valid(patient):
    form = TriageForm(data={
        "triage_category": "emergency",
        "presenting_condition": "Chest pain",
    })
    assert form.is_valid()


def test_triage_form_requires_category():
    form = TriageForm(data={"presenting_condition": "Chest pain"})
    assert not form.is_valid()


def test_rapid_register_form_valid(nurse):
    form = RapidRegisterForm(data={
        "first_name": "John",
        "last_name": "Doe",
        "sex": "male",
        "triage_category": "urgent",
        "presenting_condition": "Severe headache",
    })
    assert form.is_valid()
    patient, triage = form.save(registered_by=nurse)
    assert patient.pk is not None
    assert triage.pk is not None
    assert triage.rapid_registration is True


# --- views ---

def test_triage_view_requires_login(client, patient):
    url = reverse("emergency:triage", args=[patient.pk])
    response = client.get(url)
    assert response.status_code == 302
    assert "login" in response.url


def test_triage_view_creates_triage(client, patient, nurse):
    client.force_login(nurse)
    url = reverse("emergency:triage", args=[patient.pk])
    response = client.post(url, {"triage_category": "urgent", "presenting_condition": "Back pain"})
    assert response.status_code == 302
    assert TriageEncounter.objects.filter(patient=patient).count() == 1


def test_queue_shows_triages(client, patient, nurse):
    services.triage_patient(patient, nurse, TriageCategory.STANDARD, "Rash")
    client.force_login(nurse)
    url = reverse("emergency:queue")
    response = client.get(url)
    assert response.status_code == 200
    assert "Standard" in response.content.decode()


def test_queue_empty_state(client, nurse):
    client.force_login(nurse)
    url = reverse("emergency:queue")
    response = client.get(url)
    assert response.status_code == 200
    assert "No patients in triage queue" in response.content.decode()


def test_rapid_register_creates_patient_and_triage(client, nurse):
    client.force_login(nurse)
    url = reverse("emergency:rapid_register")
    response = client.post(url, {
        "first_name": "Rapid",
        "last_name": "Patient",
        "sex": "male",
        "triage_category": "immediate",
        "presenting_condition": "Unconscious",
    })
    assert response.status_code == 302
    assert Patient.objects.filter(first_name="Rapid").exists()
    assert TriageEncounter.objects.filter(rapid_registration=True).count() == 1
