from django.conf import settings
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from encounters.models import Encounter
from patients.models import Patient
from pharmacy.models import Prescription


class AdmissionStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    TRANSFERRED = "transferred", "Transferred"
    DISCHARGED = "discharged", "Discharged"
    DEAD = "dead", "Dead"


class Ward(models.Model):
    name = models.CharField(max_length=100)
    department = models.CharField(max_length=100, blank=True)
    bed_count = models.PositiveIntegerField()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Bed(models.Model):
    ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name="beds")
    label = models.CharField(max_length=20)
    is_occupied = models.BooleanField(default=False)

    class Meta:
        unique_together = [("ward", "label")]

    def __str__(self):
        return f"{self.ward.name} - {self.label}"


class Admission(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="admissions")
    admitting_clinician = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="admissions")
    admission_diagnosis = models.CharField(max_length=300)
    encounter = models.ForeignKey(Encounter, on_delete=models.SET_NULL, null=True, blank=True, related_name="admissions")
    status = models.CharField(max_length=15, choices=AdmissionStatus.choices, default=AdmissionStatus.ACTIVE)
    bed = models.OneToOneField(Bed, on_delete=models.SET_NULL, null=True, blank=True, related_name="current_admission")
    admitted_at = models.DateTimeField(auto_now_add=True)
    discharged_at = models.DateTimeField(null=True, blank=True)
    discharge_disposition = models.CharField(max_length=50, blank=True)
    discharge_summary = models.TextField(blank=True)

    # §8.1.4(k): Death documentation
    cause_of_death = models.CharField(max_length=300, blank=True)
    death_certificate_issued = models.BooleanField(default=False)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-admitted_at"]

    def __str__(self):
        return f"{self.patient.patient_number} - {self.admission_diagnosis}"


class WardRoundNote(models.Model):
    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name="ward_rounds")
    clinician = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    note = models.TextField()
    diagnosis_update = models.TextField(blank=True)
    plan_update = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Round note for {self.admission.patient.patient_number} - {self.created_at.date()}"


# ── §8.1.4(g), §8.1.6(f): Medication Administration Record ──────────────


class MedicationAdministrationRecord(models.Model):
    """Tracks each administration event: who gave what, when, and the site."""

    class AdministrationRoute(models.TextChoices):
        ORAL = "oral", "Oral"
        IV = "iv", "Intravenous"
        IM = "im", "Intramuscular"
        SC = "sc", "Subcutaneous"
        TOPICAL = "topical", "Topical"
        RECTAL = "rectal", "Rectal"
        OTHER = "other", "Other"

    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name="mar_entries")
    prescription = models.ForeignKey(Prescription, on_delete=models.PROTECT, related_name="administration_records")
    administered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="mar_administrations")
    dose_given = models.CharField(max_length=80)
    route = models.CharField(max_length=20, choices=AdministrationRoute.choices)
    site = models.CharField(max_length=80, blank=True)
    administered_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-administered_at"]

    def __str__(self):
        return f"MAR: {self.prescription.drug} → {self.admission.patient.patient_number} @ {self.administered_at:%d %b %H:%M}"


# ── §8.1.4(e), §8.1.6(b): Nursing Care Plans ────────────────────────────


class NursingCarePlan(models.Model):
    """Structured care plan: problem → goal → intervention → evaluation."""

    class GoalStatus(models.TextChoices):
        ONGOING = "ongoing", "Ongoing"
        MET = "met", "Met"
        PARTIALLY_MET = "partial", "Partially Met"
        NOT_MET = "not_met", "Not Met"

    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name="care_plans")
    problem = models.CharField(max_length=300)
    goal = models.TextField()
    interventions = models.TextField()
    evaluated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="care_plans_evaluated")
    evaluation = models.TextField(blank=True)
    goal_status = models.CharField(max_length=15, choices=GoalStatus.choices, default=GoalStatus.ONGOING)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="care_plans_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Care plan: {self.problem} ({self.get_goal_status_display()})"


# ── §8.1.4(f): Fluid Balance Charts ──────────────────────────────────────


class FluidBalanceEntry(models.Model):
    """Single intake or output record. Net balance computed in the view/template."""

    class FluidType(models.TextChoices):
        ORAL = "oral", "Oral intake"
        IV_FLUID = "iv_fluid", "IV fluid"
        BLOOD = "blood", "Blood products"
        OTHER_INPUT = "other_input", "Other input"
        URINE = "urine", "Urine"
        STOOL = "stool", "Stool"
        VOMIT = "vomit", "Vomit/NG output"
        DRAIN = "drain", "Drain output"
        OTHER_OUTPUT = "other_output", "Other output"

    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name="fluid_balance_entries")
    fluid_type = models.CharField(max_length=20, choices=FluidType.choices)
    volume_ml = models.PositiveIntegerField()
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    recorded_at = models.DateTimeField(default=timezone.now)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-recorded_at"]

    def __str__(self):
        return f"{self.get_fluid_type_display()}: {self.volume_ml}ml @ {self.recorded_at:%d %b %H:%M}"

    @property
    def is_intake(self) -> bool:
        return self.fluid_type in ("oral", "iv_fluid", "blood", "other_input")


# ── §8.1.4(i), §8.1.8(e): Procedure Notes ──────────────────────────────


class ProcedureNote(models.Model):
    """Documentation for any procedure performed on an inpatient."""

    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name="procedure_notes")
    procedure_name = models.CharField(max_length=200)
    indication = models.TextField(blank=True)
    procedure_date = models.DateTimeField(default=timezone.now)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="procedures_performed")
    assistants = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="procedures_assisted")
    anaesthesia_type = models.CharField(max_length=50, blank=True)
    findings = models.TextField()
    complications = models.TextField(blank=True)
    outcome = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-procedure_date"]

    def __str__(self):
        return f"{self.procedure_name} - {self.admission.patient.patient_number} @ {self.procedure_date:%d %b %Y}"


# ── §8.1.6(a): Nursing Assessment & Problem List ─────────────────────────


class NursingAssessment(models.Model):
    """Nursing assessment: initial and ongoing, with active problem tracking."""

    class ProblemStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        RESOLVED = "resolved", "Resolved"
        IMPROVING = "improving", "Improving"

    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name="nursing_assessments")
    assessment_note = models.TextField()
    problems = models.JSONField(default=list, blank=True)
    assessed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Nursing assessments"

    def __str__(self):
        return f"Nursing assessment for {self.admission.patient.patient_number} @ {self.created_at:%d %b %H:%M}"
