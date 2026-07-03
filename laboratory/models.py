from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from encounters.models import Encounter
from patients.models import Patient
from reporting.services import raise_alert


class SpecimenType(models.TextChoices):
    BLOOD = "blood", "Blood"
    URINE = "urine", "Urine"
    STOOL = "stool", "Stool"
    SWAB = "swab", "Swab"
    OTHER = "other", "Other"


class LabOrderStatus(models.TextChoices):
    ORDERED = "ordered", "Ordered"
    SPECIMEN_COLLECTED = "specimen_collected", "Specimen collected"
    IN_PROGRESS = "in_progress", "In progress"
    RESULTED = "resulted", "Resulted"
    VERIFIED = "verified", "Verified"
    CANCELLED = "cancelled", "Cancelled"


class LabTest(models.Model):
    name = models.CharField(max_length=150)
    loinc_code = models.CharField(max_length=30, blank=True)
    specimen_type = models.CharField(max_length=20, choices=SpecimenType.choices)
    normal_range_low = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    normal_range_high = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unit = models.CharField(max_length=30, blank=True)
    is_critical_if_outside_range = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class LabOrder(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="lab_orders")
    encounter = models.ForeignKey(Encounter, on_delete=models.SET_NULL, null=True, blank=True, related_name="lab_orders")
    ordered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="lab_orders")
    test = models.ForeignKey(LabTest, on_delete=models.PROTECT)
    status = models.CharField(max_length=25, choices=LabOrderStatus.choices, default=LabOrderStatus.ORDERED)
    specimen_barcode = models.CharField(max_length=40, blank=True)
    collected_at = models.DateTimeField(null=True, blank=True)
    collected_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.test} for {self.patient.patient_number}"

    def mark_collected(self, user):
        self.status = LabOrderStatus.SPECIMEN_COLLECTED
        self.collected_by = user
        self.collected_at = timezone.now()
        if not self.specimen_barcode:
            self.specimen_barcode = f"LAB{timezone.now():%Y%m%d}{self.pk:06d}"
        self.save(update_fields=["status", "collected_by", "collected_at", "specimen_barcode"])


class LabResult(models.Model):
    order = models.OneToOneField(LabOrder, on_delete=models.CASCADE, related_name="result")
    value_numeric = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    value_text = models.CharField(max_length=100, blank=True)
    is_abnormal = models.BooleanField(default=False, editable=False)
    is_critical = models.BooleanField(default=False, editable=False)
    entered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="lab_results_entered")
    entered_at = models.DateTimeField(auto_now_add=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="lab_results_verified")
    verified_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-entered_at"]

    def save(self, *args, **kwargs):
        test = self.order.test
        self.is_abnormal = False
        self.is_critical = False
        if self.value_numeric is not None:
            value = Decimal(self.value_numeric)
            low = test.normal_range_low
            high = test.normal_range_high
            self.is_abnormal = (low is not None and value < low) or (high is not None and value > high)
            self.is_critical = self.is_abnormal and test.is_critical_if_outside_range
        is_new = self._state.adding
        super().save(*args, **kwargs)
        next_status = LabOrderStatus.VERIFIED if self.verified_by_id else LabOrderStatus.RESULTED
        if self.order.status != next_status:
            self.order.status = next_status
            self.order.save(update_fields=["status"])
        if is_new and self.is_critical:
            raise_alert(
                patient=self.order.patient,
                source="lab",
                severity="critical",
                message=f"Critical {test.name} result for {self.order.patient.patient_number}: {self.display_value}",
            )

    @property
    def display_value(self):
        if self.value_numeric is not None:
            return f"{self.value_numeric:g} {self.order.test.unit}".strip()
        return self.value_text or "No value"

    def __str__(self):
        return f"{self.order.test}: {self.display_value}"

