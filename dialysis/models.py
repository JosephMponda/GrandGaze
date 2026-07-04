from decimal import Decimal

from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from patients.models import Patient


class CKDStage(models.TextChoices):
    STAGE_1 = "stage_1", "Stage 1 (eGFR ≥ 90)"
    STAGE_2 = "stage_2", "Stage 2 (eGFR 60–89)"
    STAGE_3A = "stage_3a", "Stage 3a (eGFR 45–59)"
    STAGE_3B = "stage_3b", "Stage 3b (eGFR 30–44)"
    STAGE_4 = "stage_4", "Stage 4 (eGFR 15–29)"
    STAGE_5 = "stage_5", "Stage 5 (eGFR < 15)"


class VascularAccess(models.TextChoices):
    AV_FISTULA = "av_fistula", "AV Fistula"
    AV_GRAFT = "av_graft", "AV Graft"
    TUNNELED_CATHETER = "tunneled_catheter", "Tunneled Catheter"
    TEMPORARY_CATHETER = "temporary_catheter", "Temporary Catheter"
    PERITONEAL = "peritoneal", "Peritoneal"


class CKDDiagnosis(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="ckd_diagnoses")
    stage = models.CharField(max_length=10, choices=CKDStage.choices)
    diagnosed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    diagnosed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-diagnosed_at"]

    def __str__(self):
        return f"{self.patient.patient_number} — {self.get_stage_display()}"


class DialysisPrescription(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="dialysis_prescriptions")
    frequency_per_week = models.PositiveIntegerField()
    target_fluid_removal_l = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    vascular_access = models.CharField(max_length=20, choices=VascularAccess.choices, default=VascularAccess.AV_FISTULA)
    prescribed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.patient.patient_number} — {self.frequency_per_week}x/week"

    @property
    def expected_sessions_per_week(self) -> int:
        return max(self.frequency_per_week, 1)


class DialysisSession(models.Model):
    prescription = models.ForeignKey(DialysisPrescription, on_delete=models.PROTECT, related_name="sessions")
    session_date = models.DateField()
    pre_weight_kg = models.DecimalField(max_digits=5, decimal_places=1)
    post_weight_kg = models.DecimalField(max_digits=5, decimal_places=1)
    fluid_removed_l = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    complications = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    conducted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-session_date"]

    def __str__(self):
        return f"{self.prescription.patient.patient_number} — {self.session_date}"

    def save(self, *args, **kwargs):
        if self.fluid_removed_l is None and self.pre_weight_kg and self.post_weight_kg:
            pre = Decimal(str(self.pre_weight_kg))
            post = Decimal(str(self.post_weight_kg))
            self.fluid_removed_l = pre - post
        super().save(*args, **kwargs)
