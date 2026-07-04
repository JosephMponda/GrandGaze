import pytest
from django.contrib.auth.models import Group, User
from rest_framework.test import APIClient

from accounts.models import Profile, Role
from patients.models import Patient

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


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


def test_patient_bundle_returns_fhir_shape(api_client, patient, nurse_user):
    api_client.force_authenticate(user=nurse_user)
    url = f"/api/interop/patient/{patient.pk}/bundle/"
    response = api_client.get(url)
    assert response.status_code == 200
    data = response.json()
    assert data["resourceType"] == "Bundle"
    assert data["type"] == "collection"
    assert len(data["entry"]) >= 1
    patient_resource = data["entry"][0]["resource"]
    assert patient_resource["resourceType"] == "Patient"
    assert patient_resource["id"] == f"Patient/{patient.pk}"
    assert len(patient_resource["name"]) >= 1


def test_patient_bundle_requires_auth(api_client, patient):
    url = f"/api/interop/patient/{patient.pk}/bundle/"
    response = api_client.get(url)
    assert response.status_code == 403
