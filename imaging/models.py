from django.conf import settings
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from encounters.models import Encounter
from patients.models import Patient
from reporting.services import raise_alert


class ImagingStatus(models.TextChoices):
    REQUESTED = "requested", "Requested"
    SCHEDULED = "scheduled", "Scheduled"
    COMPLETED = "completed", "Completed"
    REPORTED = "reported", "Reported"


class ImagingModality(models.Model):
    name = models.CharField(max_length=100, unique=True)
    requires_pregnancy_check = models.BooleanField(default=False)
    is_mvp_supported = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ImagingRequest(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="imaging_requests")
    encounter = models.ForeignKey(Encounter, on_delete=models.SET_NULL, null=True, blank=True, related_name="imaging_requests")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="imaging_requests")
    modality = models.ForeignKey(ImagingModality, on_delete=models.PROTECT)
    clinical_indication = models.TextField()
    pregnancy_status_checked = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=ImagingStatus.choices, default=ImagingStatus.REQUESTED)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.modality} for {self.patient.patient_number}"


class ImagingReport(models.Model):
    request = models.OneToOneField(ImagingRequest, on_delete=models.CASCADE, related_name="report")
    findings = models.TextField()
    impression = models.TextField()
    is_critical_finding = models.BooleanField(default=False)
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="imaging_reports")
    reported_at = models.DateTimeField(default=timezone.now)
    image_reference = models.CharField(max_length=255, blank=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-reported_at"]

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if self.request.status != ImagingStatus.REPORTED:
            self.request.status = ImagingStatus.REPORTED
            self.request.save(update_fields=["status"])
        if is_new and self.is_critical_finding:
            raise_alert(
                patient=self.request.patient,
                source="imaging",
                severity="critical",
                message=f"Critical {self.request.modality.name} finding for {self.request.patient.patient_number}",
            )

    def __str__(self):
        return f"Report for {self.request}"

