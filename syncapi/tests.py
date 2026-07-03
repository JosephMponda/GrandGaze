import pytest
from django.contrib.auth.models import Group, User
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Profile, Role
from patients.models import Patient

from .models import SyncSubmission

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
    return Patient.objects.create(first_name="Grace", last_name="Banda", sex="female", registered_by=nurse_user)


@pytest.fixture
def api_client():
    return APIClient()


# --- idempotent replay ---


def test_duplicate_client_uuid_returns_same_result(api_client, nurse_user):
    api_client.force_authenticate(user=nurse_user)
    payload = {
        "client_uuid": "abc-123",
        "form_type": "patient_registration",
        "payload_json": {
            "first_name": "John",
            "last_name": "Phiri",
            "sex": "male",
        },
    }
    r1 = api_client.post("/api/sync/submit/", payload, format="json")
    assert r1.status_code == 200
    assert r1.data["status"] == "applied"

    r2 = api_client.post("/api/sync/submit/", payload, format="json")
    assert r2.status_code == 200
    assert r2.data["status"] == "already_applied"


# --- conflict detection ---


def test_vitals_on_signed_encounter_produces_conflict(api_client, nurse_user, patient):
    from encounters.models import Encounter
    from encounters.services import sign_encounter

    enc = Encounter.objects.create(patient=patient, clinician=nurse_user, presenting_complaint="Test")
    sign_encounter(encounter=enc, clinician=nurse_user)

    api_client.force_authenticate(user=nurse_user)
    payload = {
        "client_uuid": "def-456",
        "form_type": "vitals_entry",
        "payload_json": {
            "encounter_id": enc.pk,
            "heart_rate": 80,
        },
    }
    r = api_client.post("/api/sync/submit/", payload, format="json")
    assert r.status_code == 200
    assert r.data["status"] == "conflict"
    assert "already signed" in r.data["conflict_note"]


# --- sync status ---


def test_sync_status_returns_user_submissions(api_client, nurse_user):
    api_client.force_authenticate(user=nurse_user)
    SyncSubmission.objects.create(
        client_uuid="status-test-1",
        form_type="test",
        payload_json={},
        submitted_by=nurse_user,
        status=SyncSubmission.Status.APPLIED,
    )
    r = api_client.get("/api/sync/status/")
    assert r.status_code == 200
    uuids = [s["client_uuid"] for s in r.data]
    assert "status-test-1" in uuids


# --- validation ---


def test_sync_submit_requires_auth(api_client):
    r = api_client.post("/api/sync/submit/", {"client_uuid": "x", "form_type": "x", "payload_json": {}}, format="json")
    assert r.status_code == 403
