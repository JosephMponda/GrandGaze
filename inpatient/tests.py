import pytest
from django.contrib.auth.models import Group, User
from django.test import Client
from django.urls import reverse

from patients.models import Patient

from .models import Admission, AdmissionStatus, Bed, Ward
from .services import (
    add_ward_round_note,
    admit_patient,
    assign_bed,
    available_beds,
    discharge,
    transfer_patient,
    ward_occupancy,
)


@pytest.fixture
def patient(db):
    return Patient.objects.create(
        patient_number="TEST-001", first_name="Alice", last_name="Zulu", registered_by=User.objects.create(username="doc"),
    )


@pytest.fixture
def clinician(db):
    Group.objects.get_or_create(name="Clinician")
    u = User.objects.create_user(username="clinician1", password="test123")
    u.groups.add(Group.objects.get(name="Clinician"))
    return u


@pytest.fixture
def ward(db):
    return Ward.objects.create(name="Medical Ward", department="Medicine", bed_count=4)


@pytest.fixture
def beds(db, ward):
    return [Bed.objects.create(ward=ward, label=f"A-{i:02d}") for i in range(1, 5)]


class TestServices:
    def test_admit_patient(self, patient, clinician):
        a = admit_patient(patient, clinician, "Severe malaria")
        assert a.patient == patient
        assert a.status == AdmissionStatus.ACTIVE

    def test_admit_with_bed(self, patient, clinician, beds):
        a = admit_patient(patient, clinician, "Pneumonia", bed=beds[0])
        assert a.bed == beds[0]
        beds[0].refresh_from_db()
        assert beds[0].is_occupied

    def test_discharge_frees_bed(self, patient, clinician, beds):
        a = admit_patient(patient, clinician, "Malaria", bed=beds[0])
        discharge(a, clinician, summary="Recovered")
        a.refresh_from_db()
        assert a.status == AdmissionStatus.DISCHARGED
        assert a.discharged_at is not None
        beds[0].refresh_from_db()
        assert not beds[0].is_occupied

    def test_transfer_frees_old_bed(self, patient, clinician, beds):
        a = admit_patient(patient, clinician, "TB", bed=beds[0])
        transfer_patient(a, beds[1])
        a.refresh_from_db()
        assert a.bed == beds[1]
        beds[0].refresh_from_db()
        assert not beds[0].is_occupied
        assert beds[1].is_occupied

    def test_ward_occupancy(self, patient, clinician, ward, beds):
        admit_patient(patient, clinician, "Malaria", bed=beds[0])
        occ = ward_occupancy(ward)
        assert occ["occupied_beds"] == 1
        assert occ["total_beds"] == 4
        assert occ["free_beds"] == 3

    def test_ward_round_note(self, patient, clinician, beds):
        a = admit_patient(patient, clinician, "CKD", bed=beds[0])
        note = add_ward_round_note(a, clinician, "Patient stable", plan_update="Continue meds")
        assert note.admission == a
        assert note.clinician == clinician

    def test_available_beds_excludes_occupied(self, patient, clinician, ward, beds):
        admit_patient(patient, clinician, "Malaria", bed=beds[0])
        admit_patient(patient, clinician, "HIV", bed=beds[1])
        avail = available_beds(ward)
        assert len(avail) == 2  # 4 total, 2 occupied


def test_beds_for_ward_returns_valid_html(db, ward, beds, clinician):
    """H7: beds_for_ward must return valid select HTML, not crash on escaping."""
    from django.test import Client
    c = Client()
    c.force_login(clinician)
    response = c.get(reverse("inpatient:beds_for_ward"), {"ward": ward.pk})
    assert response.status_code == 200
    assert "<select" in response.content.decode()
    assert response["Content-Type"] == "text/html; charset=utf-8"


class TestViews:
    def test_admit_requires_clinician_role(self, patient, clinician):
        c = Client()
        c.force_login(clinician)
        resp = c.post(reverse("inpatient:admit", args=[patient.pk]), {"diagnosis": "Malaria"})
        assert resp.status_code == 302
        assert Admission.objects.count() == 1

    def test_admit_permission_denied(self, patient):
        u = User.objects.create_user(username="nobody", password="test123")
        c = Client()
        c.force_login(u)
        resp = c.get(reverse("inpatient:admit", args=[patient.pk]))
        assert resp.status_code == 403

    def test_discharge_view(self, patient, clinician, beds):
        a = admit_patient(patient, clinician, "Malaria", bed=beds[0])
        c = Client()
        c.force_login(clinician)
        resp = c.post(reverse("inpatient:admission_detail", args=[a.pk]), {"action": "discharge", "disposition": "discharged", "summary": "Well"})
        assert resp.status_code == 302
        a.refresh_from_db()
        assert a.status == AdmissionStatus.DISCHARGED

    def test_ward_round_view(self, patient, clinician, beds):
        a = admit_patient(patient, clinician, "Malaria", bed=beds[0])
        c = Client()
        c.force_login(clinician)
        resp = c.post(reverse("inpatient:admission_detail", args=[a.pk]), {"action": "ward_round", "note": "Doing well"})
        assert resp.status_code == 302
        assert a.ward_rounds.count() == 1
