from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords


class Severity(models.TextChoices):
    INFO = "info", "Info"
    WARNING = "warning", "Warning"
    CRITICAL = "critical", "Critical"


class AlertEvent(models.Model):
    """Central alert hub. Brief §9.2 (critical result alerts, abnormal vital
    triggers). Owned by Engineer E per AGENTS.md module map - this is the
    minimal slice (model + raise_alert()) that Engineer B's vitals module
    hard-depends on; the rest of `reporting` (dashboards etc.) is Engineer E's.
    """

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="alerts")
    source = models.CharField(max_length=30)  # vitals/lab/imaging/pharmacy/system
    severity = models.CharField(max_length=10, choices=Severity.choices)
    message = models.TextField()
    raised_at = models.DateTimeField(auto_now_add=True)
    acknowledged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-raised_at"]

    def __str__(self):
        return f"[{self.severity}] {self.source}: {self.message[:50]}"
