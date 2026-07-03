from django.utils import timezone

from .models import AlertEvent


def raise_alert(*, patient, source: str, severity: str, message: str) -> AlertEvent:
    """Single entry point for firing a patient-safety alert. Other apps must
    call this rather than building a second alerting system (Engineer B spec §2).
    """
    return AlertEvent.objects.create(patient=patient, source=source, severity=severity, message=message)


def unacknowledged_alerts(limit=20):
    """Return unacknowledged alerts ordered by most recent first."""
    return AlertEvent.objects.filter(acknowledged_by__isnull=True)[:limit]


def acknowledge(alert, user):
    """Mark an alert as acknowledged by the given user."""
    alert.acknowledged_by = user
    alert.acknowledged_at = timezone.now()
    alert.save(update_fields=["acknowledged_by", "acknowledged_at"])
    return alert
