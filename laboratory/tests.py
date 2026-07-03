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
    return Patient.objects.create(
        patient_number="MUST-202607-00001",
        first_name="Grace",
        last_name="Banda",
        sex="female",
        registered_by=clinician,
    )


@pytest.fixture
def creatinine_test():
    return LabTest.objects.create(
        name="Creatinine",
        specimen_type=SpecimenType.BLOOD,
        normal_range_low=Decimal("40"),
        normal_range_high=Decimal("120"),
        unit="umol/L",
        is_critical_if_outside_range=True,
    )


def test_critical_lab_result_flags_and_fires_alert(patient, clinician, labtech, creatinine_test):
    encounter = Encounter.objects.create(patient=patient, clinician=clinician, presenting_complaint="Review")
    order = services.create_order(patient, creatinine_test, clinician, encounter)

    result = services.enter_result(order, {"value_numeric": Decimal("300"), "value_text": "", "notes": ""}, labtech)

    assert result.is_abnormal is True
    assert result.is_critical is True
    assert result.order.status == LabOrderStatus.RESULTED
    assert AlertEvent.objects.filter(patient=patient, source="lab", severity="critical").exists()


def test_lab_result_verification_requires_second_user(patient, clinician, labtech, creatinine_test):
    order = services.create_order(patient, creatinine_test, clinician)
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


# --- Boundary-value tests for abnormal/critical flagging ---


def test_normal_result_within_range_not_flagged(patient, clinician, labtech, creatinine_test):
    """Value exactly at low boundary should be normal."""
    encounter = Encounter.objects.create(patient=patient, clinician=clinician, presenting_complaint="Review")
    order = services.create_order(patient, creatinine_test, clinician, encounter)
    result = services.enter_result(
        order, {"value_numeric": Decimal("40"), "value_text": "", "notes": ""}, labtech
    )
    assert result.is_abnormal is False
    assert result.is_critical is False


def test_normal_result_at_high_boundary_not_flagged(patient, clinician, labtech, creatinine_test):
    """Value exactly at high boundary should be normal."""
    encounter = Encounter.objects.create(patient=patient, clinician=clinician, presenting_complaint="Review")
    order = services.create_order(patient, creatinine_test, clinician, encounter)
    result = services.enter_result(
        order, {"value_numeric": Decimal("120"), "value_text": "", "notes": ""}, labtech
    )
    assert result.is_abnormal is False
    assert result.is_critical is False


def test_abnormal_result_below_low_range_flagged(patient, clinician, labtech, creatinine_test):
    """Value just below low boundary should be abnormal."""
    encounter = Encounter.objects.create(patient=patient, clinician=clinician, presenting_complaint="Review")
    order = services.create_order(patient, creatinine_test, clinician, encounter)
    result = services.enter_result(
        order, {"value_numeric": Decimal("39.99"), "value_text": "", "notes": ""}, labtech
    )
    assert result.is_abnormal is True


def test_abnormal_result_above_high_range_flagged(patient, clinician, labtech, creatinine_test):
    """Value just above high boundary should be abnormal."""
    encounter = Encounter.objects.create(patient=patient, clinician=clinician, presenting_complaint="Review")
    order = services.create_order(patient, creatinine_test, clinician, encounter)
    result = services.enter_result(
        order, {"value_numeric": Decimal("120.01"), "value_text": "", "notes": ""}, labtech
    )
    assert result.is_abnormal is True


def test_abnormal_but_not_critical_when_flag_off(patient, clinician, labtech):
    """When is_critical_if_outside_range is False, abnormal values are not critical."""
    test = LabTest.objects.create(
        name="Potassium",
        specimen_type=SpecimenType.BLOOD,
        normal_range_low=Decimal("3.5"),
        normal_range_high=Decimal("5.5"),
        unit="mmol/L",
        is_critical_if_outside_range=False,
    )
    encounter = Encounter.objects.create(patient=patient, clinician=clinician, presenting_complaint="Review")
    order = services.create_order(patient, test, clinician, encounter)
    result = services.enter_result(
        order, {"value_numeric": Decimal("6.0"), "value_text": "", "notes": ""}, labtech
    )
    assert result.is_abnormal is True
    assert result.is_critical is False
    # No alert should fire for non-critical abnormal
    assert not AlertEvent.objects.filter(patient=patient, source="lab").exists()
