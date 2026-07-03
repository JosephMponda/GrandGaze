from decimal import Decimal

import pytest
from django.contrib.auth.models import Group, User

from accounts.models import Profile, Role
from encounters.models import Encounter
from patients.models import Patient
from reporting.models import AlertEvent

from .forms import LabResultForm
from .models import LabOrderStatus, LabTest, SpecimenType
from . import services

pytestmark = pytest.mark.django_db


@pytest.fixture
def clinician():
    Group.objects.get_or_create(name="Clinician")
    user = User.objects.create_user("clinician_c", password="TestPass123!")
    Profile.objects.create(user=user, role=Role.CLINICIAN)
    user.groups.add(Group.objects.get(name="Clinician"))
    return user


@pytest.fixture
def labtech():
    Group.objects.get_or_create(name="LabTech")
    user = User.objects.create_user("labtech_c", password="TestPass123!")
    Profile.objects.create(user=user, role=Role.LAB_TECH)
    user.groups.add(Group.objects.get(name="LabTech"))
    return user


@pytest.fixture
def patient(clinician):
    return Patient.objects.create(patient_number="MUST-202607-00001", first_name="Grace", last_name="Banda", sex="female", registered_by=clinician)


def test_critical_lab_result_flags_and_fires_alert(patient, clinician, labtech):
    test = LabTest.objects.create(
        name="Creatinine",
        specimen_type=SpecimenType.BLOOD,
        normal_range_low=Decimal("40"),
        normal_range_high=Decimal("120"),
        unit="umol/L",
        is_critical_if_outside_range=True,
    )
    encounter = Encounter.objects.create(patient=patient, clinician=clinician, presenting_complaint="Review")
    order = services.create_order(patient, test, clinician, encounter)

    result = services.enter_result(order, {"value_numeric": Decimal("300"), "value_text": "", "notes": ""}, labtech)

    assert result.is_abnormal is True
    assert result.is_critical is True
    assert result.order.status == LabOrderStatus.RESULTED
    assert AlertEvent.objects.filter(patient=patient, source="lab", severity="critical").exists()


def test_lab_result_verification_requires_second_user(patient, clinician, labtech):
    test = LabTest.objects.create(name="Malaria RDT", specimen_type=SpecimenType.BLOOD)
    order = services.create_order(patient, test, clinician)
    result = services.enter_result(order, {"value_text": "Negative", "value_numeric": None, "notes": ""}, labtech)

    with pytest.raises(ValueError):
        services.verify_result(result, labtech)

    services.verify_result(result, clinician)
    result.refresh_from_db()
    assert result.verified_by == clinician
    assert result.order.status == LabOrderStatus.VERIFIED


def test_lab_result_form_requires_a_value():
    form = LabResultForm(data={"notes": "no result"})
    assert not form.is_valid()

