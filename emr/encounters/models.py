from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from patients.models import Patient


class EncounterType(models.TextChoices):
    OUTPATIENT = "outpatient", "Outpatient"
    EMERGENCY = "emergency", "Emergency"
    FOLLOW_UP = "follow_up", "Follow-up"


class EncounterStatus(models.TextChoices):
    OPEN = "open", "Open"
    CLOSED = "closed", "Closed"


class Encounter(models.Model):
    """Outpatient clinical documentation. Brief §8.1.3."""

    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="encounters")
    clinician = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="encounters")
    encounter_type = models.CharField(max_length=20, choices=EncounterType.choices, default=EncounterType.OUTPATIENT)
    status = models.CharField(max_length=10, choices=EncounterStatus.choices, default=EncounterStatus.OPEN)

    presenting_complaint = models.TextField()
    history_of_presenting_complaint = models.TextField(blank=True)
    past_medical_history = models.TextField(blank=True)
    past_surgical_history = models.TextField(blank=True)
    medication_history = models.TextField(blank=True)
    allergy_history = models.TextField(blank=True)  # free-text context; AllergyRecord below is the real safety data
    social_history = models.TextField(blank=True)
    family_history = models.TextField(blank=True)
    examination_findings = models.TextField(blank=True)
    diagnosis = models.CharField(max_length=255, blank=True)
    differential_diagnosis = models.TextField(blank=True)
    clinical_plan = models.TextField(blank=True)

    signed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="encounters_signed")
    signed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Encounter #{self.pk} — {self.patient.patient_number} ({self.get_status_display()})"

    @property
    def is_signed(self) -> bool:
        return self.signed_at is not None


class EncounterAddendum(models.Model):
    """A signed Encounter is read-only in the UI; further notes are addenda,
    not silent rewrites of signed clinical documentation (Engineer B spec §4
    — governance requirement, not a nice-to-have).
    """

    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE, related_name="addenda")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Addendum to Encounter #{self.encounter_id} by {self.author}"


class Severity(models.TextChoices):
    MILD = "mild", "Mild"
    MODERATE = "moderate", "Moderate"
    SEVERE = "severe", "Severe"


class AllergyRecord(models.Model):
    """Patient-level (not encounter-level): an allergy known from one
    encounter must alert on every future prescription. This is the model
    Pharmacy (Engineer D) queries at prescribing time via get_patient_allergies().
    """

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="allergies")
    allergen = models.CharField(max_length=200)
    reaction = models.CharField(max_length=255, blank=True)
    severity = models.CharField(max_length=10, choices=Severity.choices)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recorded_at"]

    def __str__(self):
        return f"{self.patient.patient_number}: {self.allergen} ({self.get_severity_display()})"


class ClinicalTemplate(models.Model):
    """Structured templates for common clinics — brief §8.1.3."""

    name = models.CharField(max_length=150)
    specialty = models.CharField(max_length=100, blank=True)
    fields_json = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name
