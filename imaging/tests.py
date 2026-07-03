import pytest
from django.contrib.auth.models import Group, User

from accounts.models import Profile, Role
from patients.models import Patient
from reporting.models import AlertEvent

from .forms import ImagingRequestForm
from .models import ImagingModality
from . import services

pytestmark = pytest.mark.django_db


@pytest.fixture
def clinician():
    Group.objects.get_or_create(name="Clinician")
    user = User.objects.create_user("clinician_i", password="TestPass123!")
    Profile.objects.create(user=user, role=Role.CLINICIAN)
    user.groups.add(Group.objects.get(name="Clinician"))
    return user


@pytest.fixture
def radiographer():
    Group.objects.get_or_create(name="Radiographer")
    user = User.objects.create_user("radiographer_i", password="TestPass123!")
    Profile.objects.create(user=user, role=Role.RADIOGRAPHER)
    user.groups.add(Group.objects.get(name="Radiographer"))
    return user


@pytest.fixture
def patient(clinician):
    return Patient.objects.create(
        patient_number="MUST-202607-00002",
        first_name="Mary",
        last_name="Phiri",
        sex="female",
        registered_by=clinician,
    )


@pytest.fixture
def xray_modality():
    """Use the seed-created X-ray modality (avoids UNIQUE conflict)."""
    modality, _ = ImagingModality.objects.get_or_create(
        name="X-ray",
        defaults={"requires_pregnancy_check": True, "is_mvp_supported": True},
    )
    return modality


def test_pregnancy_status_gate_blocks_required_modality(xray_modality):
    form = ImagingRequestForm(
        data={"modality": xray_modality.pk, "clinical_indication": "Cough"}
    )
    assert not form.is_valid()
    assert "pregnancy_status_checked" in form.errors


def test_critical_imaging_report_fires_alert(patient, clinician, radiographer, xray_modality):
    request = services.create_request(
        patient, xray_modality, clinician, "Chest pain", pregnancy_status_checked=True
    )

    report = services.enter_report(
        request,
        {
            "findings": "Large pneumothorax",
            "impression": "Urgent review",
            "is_critical_finding": True,
            "image_reference": "XR-001",
        },
        radiographer,
    )

    assert report.is_critical_finding is True
    assert AlertEvent.objects.filter(
        patient=patient, source="imaging", severity="critical"
    ).exists()
