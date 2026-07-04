import pytest
from django.contrib.auth.models import Group, User
from django.db import connection
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Profile, Role
from patients.models import Patient

from .models import SyncSubmission

pytestmark = pytest.mark.django_db

# check_possible_duplicate()'s fuzzy-match branch uses TrigramSimilarity,
# which is PostgreSQL-only (same constraint patients/tests.py documents for
# test_forged_confirmation_id_does_not_bypass_duplicate_check). Any
# patient_registration sync submission with first_name+last_name set now
# exercises that branch, so it needs a real vendor check rather than an
# unconditional skip - run these against Postgres (see root README) for
# real coverage; per CHANGES_SUMMARY.md #6, an sqlite pass/skip proves nothing.
requires_postgres = pytest.mark.skipif(
    connection.vendor != "postgresql",
    reason="TrigramSimilarity requires PostgreSQL; SQLite used for test isolation",
)


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


@requires_postgres
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


# --- patient-safety: offline registration must not bypass duplicate check ---
#
# Both tests below call check_possible_duplicate() with first_name AND
# last_name set, which exercises its TrigramSimilarity fuzzy-match branch -
# PostgreSQL-only, same reason patients/tests.py skips
# test_forged_confirmation_id_does_not_bypass_duplicate_check under the
# default sqlite test run. Run these against Postgres (see root README) to
# get real coverage; per CHANGES_SUMMARY.md #6, don't trust an sqlite skip
# as proof the code path works.


@requires_postgres
def test_patient_registration_with_matching_national_id_produces_conflict(api_client, nurse_user):
    """Regression test for the bug where syncapi.dispatch._handle_patient_registration
    called register_patient() directly, skipping check_possible_duplicate() -
    silently letting offline-synced registrations bypass the same duplicate-patient
    safety net the online registration view enforces."""
    Patient.objects.create(
        first_name="John", last_name="Phiri", sex="male",
        national_id="MW-12345", registered_by=nurse_user,
    )

    api_client.force_authenticate(user=nurse_user)
    payload = {
        "client_uuid": "dup-789",
        "form_type": "patient_registration",
        "payload_json": {
            "first_name": "Jon", "last_name": "Phiri", "sex": "male",
            "national_id": "MW-12345",
        },
    }
    r = api_client.post("/api/sync/submit/", payload, format="json")
    assert r.status_code == 200
    assert r.data["status"] == "conflict"
    assert Patient.objects.filter(national_id_lookup__isnull=False).count() == 1  # no second patient created


@requires_postgres
def test_patient_registration_confirmed_not_duplicate_proceeds(api_client, nurse_user):
    candidate = Patient.objects.create(
        first_name="John", last_name="Phiri", sex="male",
        national_id="MW-99999", registered_by=nurse_user,
    )

    api_client.force_authenticate(user=nurse_user)
    payload = {
        "client_uuid": "dup-confirmed-1",
        "form_type": "patient_registration",
        "payload_json": {
            "first_name": "Jonathan", "last_name": "Phiri", "sex": "male",
            "confirmed_not_duplicate_of": candidate.pk,
        },
    }
    r = api_client.post("/api/sync/submit/", payload, format="json")
    assert r.status_code == 200
    assert r.data["status"] == "applied"


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
