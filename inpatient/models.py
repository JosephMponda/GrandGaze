from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from encounters.models import Encounter
from patients.models import Patient


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
        return f"{self.ward.name} — {self.label}"


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

    history = HistoricalRecords()

    class Meta:
        ordering = ["-admitted_at"]

    def __str__(self):
        return f"{self.patient.patient_number} — {self.admission_diagnosis}"


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
        return f"Round note for {self.admission.patient.patient_number} — {self.created_at.date()}"
