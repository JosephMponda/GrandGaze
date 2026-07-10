import pytest
from django.contrib.auth.models import Group, User
from django.test import Client
from django.urls import reverse

from patients.models import Patient

from .models import DialysisPrescription, DialysisSession
from .services import missed_sessions, prescribe_dialysis, record_ckd_diagnosis, record_session


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
def rx(db, patient, clinician):
    return prescribe_dialysis(patient, frequency_per_week=3, prescribed_by=clinician)


class TestServices:
    def test_record_ckd_diagnosis(self, patient, clinician):
        d = record_ckd_diagnosis(patient, "stage_3a", clinician, notes="eGFR 52")
        assert d.patient == patient
        assert d.get_stage_display() == "Stage 3a (eGFR 45–59)"

    def test_prescribe_dialysis(self, patient, clinician):
        rx = prescribe_dialysis(patient, frequency_per_week=3, prescribed_by=clinician, target_fluid_removal_l=2.5)
        assert rx.frequency_per_week == 3
        assert rx.is_active

    def test_record_session_sets_fluid_removed(self, patient, clinician, rx):
        from decimal import Decimal
        s = record_session(rx, clinician, {
            "session_date": "2026-07-04",
            "pre_weight_kg": "70.0",
            "post_weight_kg": "67.5",
            "complications": "",
            "notes": "",
        })
        assert s.fluid_removed_l == Decimal("2.5")

    def test_missed_sessions(self, patient, clinician, rx):
        from datetime import date, timedelta
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        # heuristic expects Mon/Tue/Wed for 3x/week - record one of them
        record_day = week_start  # Monday
        record_session(rx, clinician, {
            "session_date": record_day.isoformat(),
            "pre_weight_kg": "70.0",
            "post_weight_kg": "68.0",
            "complications": "",
            "notes": "",
        })
        missed = missed_sessions(rx)
        assert record_day not in missed
        assert len(missed) <= 2  # max 3x/week, 1 recorded, up to 2 missed


class TestViews:
    def test_patient_tab_requires_login(self, patient):
        c = Client()
        resp = c.get(reverse("dialysis:patient_tab", args=[patient.pk]))
        assert resp.status_code == 302

    def test_patient_tab_shows_data(self, patient, clinician, rx):
        c = Client()
        c.force_login(clinician)
        resp = c.get(reverse("dialysis:patient_tab", args=[patient.pk]))
        assert resp.status_code == 200
        assert "Dialysis" in resp.content.decode()

    def test_record_session_creates_session(self, patient, clinician, rx):
        c = Client()
        c.force_login(clinician)
        resp = c.post(reverse("dialysis:record_session", args=[rx.pk]), {
            "pre_weight_kg": "72.0",
            "post_weight_kg": "69.5",
            "complications": "",
            "notes": "",
        })
        assert resp.status_code == 302
        assert DialysisSession.objects.count() == 1

    def test_record_session_missing_weight_errors(self, patient, clinician, rx):
        c = Client()
        c.force_login(clinician)
        resp = c.post(reverse("dialysis:record_session", args=[rx.pk]), {
            "pre_weight_kg": "",
            "post_weight_kg": "",
            "complications": "",
            "notes": "",
        })
        assert resp.status_code == 200  # re-renders with error
        assert DialysisSession.objects.count() == 0

    def test_dashboard_renders_without_crash(self, clinician, rx):
        c = Client()
        c.force_login(clinician)
        resp = c.get(reverse("dialysis:dashboard"))
        assert resp.status_code == 200
        assert "Dialysis Dashboard" in resp.content.decode()
