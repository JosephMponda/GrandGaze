from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords


class TriageCategory(models.TextChoices):
    IMMEDIATE = "immediate", "Immediate (Resuscitation)"
    EMERGENCY = "emergency", "Emergency"
    URGENT = "urgent", "Urgent"
    STANDARD = "standard", "Standard"
    NON_URGENT = "non_urgent", "Non-Urgent"


class TriageOutcome(models.TextChoices):
    DISCHARGED = "discharged", "Discharged"
    ADMITTED = "admitted", "Admitted"
    REFERRED = "referred", "Referred"
    DEAD = "dead", "Dead"


CATEGORY_ORDER = {
    TriageCategory.IMMEDIATE: 0,
    TriageCategory.EMERGENCY: 1,
    TriageCategory.URGENT: 2,
    TriageCategory.STANDARD: 3,
    TriageCategory.NON_URGENT: 4,
}


class TriageEncounter(models.Model):
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.CASCADE, related_name="triage_encounters"
    )
    triaged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="triage_encounters"
    )
    triage_category = models.CharField(max_length=20, choices=TriageCategory.choices)
    presenting_condition = models.TextField()
    outcome = models.CharField(max_length=20, choices=TriageOutcome.choices, blank=True, null=True)
    disposition_note = models.TextField(blank=True)
    rapid_registration = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.patient} - {self.get_triage_category_display()}"
