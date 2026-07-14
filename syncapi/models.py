from django.conf import settings
from django.db import models


class SyncSubmission(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPLIED = "applied", "Applied"
        CONFLICT = "conflict", "Conflict"
        REJECTED = "rejected", "Rejected"

    client_uuid = models.CharField(max_length=255, unique=True)
    form_type = models.CharField(max_length=50)
    payload_json = models.JSONField()
    # Returned on every idempotent replay so a client can map a local record
    # to its server record even if it lost the first successful response.
    result_json = models.JSONField(default=dict, blank=True)
    patient = models.ForeignKey("patients.Patient", on_delete=models.SET_NULL, null=True, blank=True)
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    received_at = models.DateTimeField(auto_now_add=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    conflict_note = models.TextField(blank=True)

    class Meta:
        ordering = ["-received_at"]

    def __str__(self):
        return f"{self.form_type} ({self.client_uuid[:12]}…) - {self.status}"


class SyncConflict(models.Model):
    submission = models.OneToOneField(SyncSubmission, on_delete=models.CASCADE, related_name="conflict")
    conflicting_record_description = models.TextField()
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Conflict: {self.submission.client_uuid[:12]}…"
