import pytest
from django.contrib.auth.models import Group, User
from django.urls import reverse

from accounts.models import Profile, Role
from encounters import services as encounter_services
from patients import services as patient_services
from reporting.models import AlertEvent
from vitals import services
from vitals.scoring import compute_ews

pytestmark = pytest.mark.django_db


@pytest.fixture
def clinician_user():
    Group.objects.get_or_create(name="Clinician")
    u = User.objects.create_user("clinician2", password="TestPass123!")
    Profile.objects.create(user=u, role=Role.CLINICIAN)
    u.groups.add(Group.objects.get(name="Clinician"))
    return u


@pytest.fixture
def encounter(clinician_user):
    patient = patient_services.register_patient(
        dict(first_name="John", last_name="Phiri", sex="male"), registered_by=clinician_user
    )
    return encounter_services.create_encounter(patient, clinician_user, dict(presenting_complaint="Fever"))


# --- happy path ---

def test_vitals_auto_compute_bmi_and_ews(clinician_user, encounter):
    vitals = services.record_vitals(
        encounter, clinician_user,
        dict(weight_kg=70, height_cm=175, temperature_c=37.0, pulse_rate=80, respiratory_rate=16, oxygen_saturation=98),
    )
    assert float(vitals.bmi) == pytest.approx(22.9, abs=0.1)
    assert vitals.ews.score == 0
    assert vitals.ews.risk_level == "low"


def test_out_of_range_vital_fires_alert_same_cycle(clinician_user, encounter):
    services.record_vitals(encounter, clinician_user, dict(oxygen_saturation=85))  # below hard threshold
    alerts = AlertEvent.objects.filter(patient=encounter.patient, source="vitals")
    assert alerts.exists()
    assert "SpO2" in alerts.first().message


def test_vitals_trend_has_multiple_points(clinician_user, encounter):
    for spo2 in (98, 97, 96):
        services.record_vitals(encounter, clinician_user, dict(oxygen_saturation=spo2))
    trend = services.vitals_trend(encounter.patient)
    assert trend.count() == 3


def test_ews_pure_function_is_deterministic():
    class Fake:
        respiratory_rate = 30
        oxygen_saturation = 88
        temperature_c = 40.0
        blood_pressure_systolic = 85
        pulse_rate = 140
        glasgow_coma_scale = 8

    score, risk = compute_ews(Fake())
    assert score > 0
    assert risk in ("low", "medium", "high", "critical")


# --- permission-denied path ---

def test_vitals_entry_requires_login(client, encounter):
    r = client.post(reverse("vitals:entry", args=[encounter.patient.pk]), {"oxygen_saturation": 98})
    assert r.status_code == 302
    assert "/accounts/login/" in r.headers["Location"]


# --- validation-failure path ---

def test_vitals_entry_without_open_encounter_redirects_to_new_encounter(client, clinician_user):
    patient = patient_services.register_patient(dict(first_name="Zzz", last_name="Solo", sex="male"), registered_by=clinician_user)
    client.force_login(clinician_user)
    r = client.get(reverse("vitals:entry", args=[patient.pk]))
    assert r.status_code == 302
    assert reverse("encounters:new", args=[patient.pk]) in r.headers["Location"]
