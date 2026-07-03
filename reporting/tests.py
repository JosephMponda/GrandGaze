import pytest
from django.contrib.auth.models import Group, User
from django.urls import reverse
from django.utils import timezone

from accounts.models import Profile, Role
from reporting.models import AlertEvent
from reporting import services

pytestmark = pytest.mark.django_db


@pytest.fixture
def nurse_user():
    Group.objects.get_or_create(name="Nurse")
    u = User.objects.create_user("nurse1", password="TestPass123!")
    Profile.objects.create(user=u, role=Role.NURSE)
    u.groups.add(Group.objects.get(name="Nurse"))
    return u


@pytest.fixture
def patient(nurse_user):
    from patients.models import Patient
    return Patient.objects.create(
        first_name="Grace",
        last_name="Banda",
        sex="female",
        registered_by=nurse_user,
    )


# --- services: raise_alert ---


def test_raise_alert_creates_alert(patient):
    alert = services.raise_alert(
        patient=patient,
        source="lab",
        severity="critical",
        message="Critical lab result: Hb 5.0",
    )
    assert alert.pk is not None
    assert alert.severity == "critical"
    assert alert.source == "lab"
    assert alert.patient == patient


def test_raise_alert_sets_raised_at(patient):
    alert = services.raise_alert(
        patient=patient,
        source="vitals",
        severity="warning",
        message="Abnormal vital signs",
    )
    assert alert.raised_at is not None
    assert (timezone.now() - alert.raised_at).total_seconds() < 5


# --- services: unacknowledged_alerts ---


def test_unacknowledged_alerts_returns_only_unacknowledged(patient, nurse_user):
    services.raise_alert(patient=patient, source="lab", severity="info", message="Test 1")
    a2 = services.raise_alert(patient=patient, source="lab", severity="warning", message="Test 2")
    services.acknowledge(a2, nurse_user)

    results = services.unacknowledged_alerts()
    assert len(results) == 1
    assert results[0].message == "Test 1"


def test_unacknowledged_alerts_respects_limit(patient):
    for i in range(5):
        services.raise_alert(patient=patient, source="lab", severity="info", message=f"Test {i}")

    results = services.unacknowledged_alerts(limit=3)
    assert len(results) == 3


# --- services: acknowledge ---


def test_acknowledge_sets_user_and_timestamp(patient, nurse_user):
    alert = services.raise_alert(patient=patient, source="lab", severity="info", message="Ack test")
    services.acknowledge(alert, nurse_user)

    alert.refresh_from_db()
    assert alert.acknowledged_by == nurse_user
    assert alert.acknowledged_at is not None


# --- views ---


def test_recent_alerts_view_requires_login(client):
    url = reverse("reporting:recent_alerts")
    response = client.get(url)
    assert response.status_code == 302
    assert "login" in response.url


def test_recent_alerts_view_shows_alerts(client, patient, nurse_user):
    client.force_login(nurse_user)
    services.raise_alert(patient=patient, source="lab", severity="critical", message="Critical alert visible")

    url = reverse("reporting:recent_alerts")
    response = client.get(url)
    assert response.status_code == 200
    assert "Critical alert visible" in response.content.decode()


def test_acknowledge_alert_view_updates_alert(client, patient, nurse_user):
    client.force_login(nurse_user)
    alert = services.raise_alert(patient=patient, source="lab", severity="info", message="To acknowledge")

    url = reverse("reporting:acknowledge_alert", args=[alert.pk])
    response = client.post(url)
    assert response.status_code == 302

    alert.refresh_from_db()
    assert alert.acknowledged_by == nurse_user
