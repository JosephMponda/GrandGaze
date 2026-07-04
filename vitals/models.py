from decimal import Decimal

from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from encounters.models import Encounter
from patients.models import Patient


class PregnancyStatus(models.TextChoices):
    NOT_APPLICABLE = "n/a", "N/A"
    PREGNANT = "pregnant", "Pregnant"
    NOT_PREGNANT = "not_pregnant", "Not pregnant"
    UNKNOWN = "unknown", "Unknown"


class VitalSignSet(models.Model):
    """Brief §8.1.7."""

    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE, related_name="vitals")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="vital_sign_sets")  # denormalized for fast history queries
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    temperature_c = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    blood_pressure_systolic = models.IntegerField(null=True, blank=True)
    blood_pressure_diastolic = models.IntegerField(null=True, blank=True)
    pulse_rate = models.IntegerField(null=True, blank=True)
    respiratory_rate = models.IntegerField(null=True, blank=True)
    oxygen_saturation = models.IntegerField(null=True, blank=True)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    height_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    bmi = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)  # auto-calculated on save
    pain_score = models.IntegerField(null=True, blank=True)  # 0-10
    blood_glucose = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    glasgow_coma_scale = models.IntegerField(null=True, blank=True)
    pregnancy_status = models.CharField(max_length=15, choices=PregnancyStatus.choices, default=PregnancyStatus.NOT_APPLICABLE)

    recorded_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-recorded_at"]

    def save(self, *args, **kwargs):
        if self.weight_kg and self.height_cm:
            height_m = self.height_cm / Decimal("100")
            self.bmi = (self.weight_kg / (height_m * height_m)).quantize(Decimal("0.1"))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Vitals for {self.patient.patient_number} @ {self.recorded_at}"


class RiskLevel(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class EarlyWarningScore(models.Model):
    vital_sign_set = models.OneToOneField(VitalSignSet, on_delete=models.CASCADE, related_name="ews")
    score = models.IntegerField()
    risk_level = models.CharField(max_length=10, choices=RiskLevel.choices)
    computed_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"EWS {self.score} ({self.get_risk_level_display()})"
