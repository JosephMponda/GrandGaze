from django.conf import settings
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from encounters.models import Encounter
from patients.models import Patient


class PrescriptionStatus(models.TextChoices):
    PRESCRIBED = "prescribed", "Prescribed"
    APPROVED = "approved", "Approved"
    DISPENSED = "dispensed", "Dispensed"
    CANCELLED = "cancelled", "Cancelled"


class Drug(models.Model):
    name = models.CharField(max_length=150)
    generic_name = models.CharField(max_length=150)
    formulation = models.CharField(max_length=80)
    is_controlled = models.BooleanField(default=False)
    pediatric_max_dose_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    contraindicated_in_pregnancy = models.BooleanField(default=False)
    contraindicated_in_breastfeeding = models.BooleanField(default=False)
    contraindicated_in_renal = models.BooleanField(default=False)
    interacting_drugs = models.ManyToManyField("self", symmetrical=True, blank=True)

    class Meta:
        ordering = ["generic_name", "name"]

    def __str__(self):
        return f"{self.generic_name} ({self.formulation})"


class DrugAllergyMap(models.Model):
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name="allergy_keywords")
    allergen_keyword = models.CharField(max_length=100)

    class Meta:
        unique_together = [("drug", "allergen_keyword")]

    def __str__(self):
        return f"{self.drug}: {self.allergen_keyword}"


class Prescription(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="prescriptions")
    encounter = models.ForeignKey(Encounter, on_delete=models.SET_NULL, null=True, blank=True, related_name="prescriptions")
    prescribed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="prescriptions")
    drug = models.ForeignKey(Drug, on_delete=models.PROTECT)
    dose = models.CharField(max_length=80)
    route = models.CharField(max_length=40)
    frequency = models.CharField(max_length=80)
    duration_days = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=PrescriptionStatus.choices, default=PrescriptionStatus.PRESCRIBED)
    safety_override_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="prescriptions_approved")
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.drug} for {self.patient.patient_number}"


class DispensingRecord(models.Model):
    prescription = models.OneToOneField(Prescription, on_delete=models.CASCADE, related_name="dispensing")
    dispensed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    dispensed_at = models.DateTimeField(default=timezone.now)
    quantity_dispensed = models.CharField(max_length=80)
    stock_note = models.CharField(max_length=200, blank=True)

    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.prescription.status != PrescriptionStatus.DISPENSED:
            self.prescription.status = PrescriptionStatus.DISPENSED
            self.prescription.save(update_fields=["status"])

    def __str__(self):
        return f"Dispensed {self.prescription}"


class StockLevel(models.Model):
    drug = models.OneToOneField(Drug, on_delete=models.CASCADE, related_name="stock")
    quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=10)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.drug.generic_name}: {self.quantity} (threshold {self.low_stock_threshold})"

    @property
    def is_low(self) -> bool:
        return self.quantity <= self.low_stock_threshold

    class Meta:
        verbose_name_plural = "Stock levels"

