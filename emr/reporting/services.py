from .models import AlertEvent


def raise_alert(*, patient, source: str, severity: str, message: str) -> AlertEvent:
    """Single entry point for firing a patient-safety alert. Other apps must
    call this rather than building a second alerting system (Engineer B spec §2).
    """
    return AlertEvent.objects.create(patient=patient, source=source, severity=severity, message=message)
