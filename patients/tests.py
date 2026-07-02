import pytest
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.urls import reverse

from accounts.models import Profile, Role
from accounts.permissions import has_role
from patients import services
from patients.models import Patient

pytestmark = pytest.mark.django_db


@pytest.fixture
def nurse_user():
    Group.objects.get_or_create(name="Nurse")
    u = User.objects.create_user("nurse1", password="TestPass123!")
    Profile.objects.create(user=u, role=Role.NURSE)
    u.groups.add(Group.objects.get(name="Nurse"))
    return u


# --- happy path ---

def test_register_patient_generates_unique_number(nurse_user):
    data = dict(first_name="Grace", last_name="Banda", sex="female", date_of_birth="1990-05-01")
    p1 = services.register_patient(data, registered_by=nurse_user)
    p2 = services.register_patient(dict(first_name="John", last_name="Phiri", sex="male"), registered_by=nurse_user)
    assert p1.patient_number != p2.patient_number
    assert p1.patient_number.startswith("MUST-")


def test_encrypted_fields_not_stored_as_plaintext(nurse_user):
    p = services.register_patient(
        dict(first_name="Grace", last_name="Banda", sex="female", national_id="MW-001", phone_number="0888111222"),
        registered_by=nurse_user,
    )
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute("SELECT national_id, phone_number FROM patients_patient WHERE id = %s", [p.id])
        raw_national_id, raw_phone = cur.fetchone()
    assert "MW-001" not in raw_national_id
    assert "0888111222" not in raw_phone
    # but the ORM transparently decrypts
    p.refresh_from_db()
    assert p.national_id == "MW-001"
    assert p.phone_number == "0888111222"


def test_exact_duplicate_detection_via_national_id(nurse_user):
    services.register_patient(
        dict(first_name="Grace", last_name="Banda", sex="female", national_id="MW-001"),
        registered_by=nurse_user,
    )
    matches = services.check_possible_duplicate(dict(national_id="MW-001"))
    assert matches.count() == 1


# --- permission-denied path ---

def test_audit_trail_denied_for_nurse(client, nurse_user):
    client.force_login(nurse_user)
    response = client.get(reverse("accounts:audit_trail"))
    assert response.status_code == 403


def test_has_role_false_for_wrong_group(nurse_user):
    assert has_role(nurse_user, "Admin") is False
    assert has_role(nurse_user, "Nurse") is True


# --- validation-failure path ---

def test_registration_form_requires_dob_or_age_estimated_flag():
    from patients.forms import PatientRegistrationForm

    form = PatientRegistrationForm(data={"first_name": "Grace", "last_name": "Banda", "sex": "female"})
    assert not form.is_valid()
    assert "age_estimated" in form.errors
