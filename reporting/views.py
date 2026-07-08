from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from encounters.models import Encounter
from laboratory.models import LabOrder
from imaging.models import ImagingRequest
from pharmacy.models import Prescription

from .models import AlertEvent
from .services import acknowledge


@login_required
def recent_alerts(request):
    """Backs the 'patients with abnormal vitals in the last 4 hours'
    dashboard widget (Engineer B spec §4). Source-agnostic view over
    AlertEvent - other modules' alerts (lab, imaging) will show here too
    once Engineer E builds out the rest of `reporting`.
    """
    since = timezone.now() - timedelta(hours=4)
    alerts = AlertEvent.objects.filter(raised_at__gte=since).select_related("patient")
    return render(request, "reporting/recent_alerts.html", {"alerts": alerts})


@login_required
def acknowledge_alert(request, alert_id):
    alert = get_object_or_404(AlertEvent, pk=alert_id)
    acknowledge(alert, request.user)
    return redirect("reporting:recent_alerts")


@login_required
def analytics_dashboard(request):
    today = timezone.now().date()

    from patients.models import Patient

    context = {
        "patients_today": Patient.objects.filter(created_at__date=today).count(),
        "open_encounters": Encounter.objects.filter(signed_at__isnull=True).count(),
        "pending_labs": LabOrder.objects.filter(status__in=["ordered", "specimen_collected", "in_progress"]).count(),
        "pending_imaging": ImagingRequest.objects.filter(status__in=["requested", "scheduled"]).count(),
        "pending_prescriptions": Prescription.objects.filter(status="prescribed").count(),
        "unacknowledged_alerts": AlertEvent.objects.filter(acknowledged_by__isnull=True).count(),
        "critical_alerts_4h": AlertEvent.objects.filter(
            severity="critical",
            raised_at__gte=timezone.now() - timedelta(hours=4),
        ).count(),
    }
    return render(request, "reporting/analytics_dashboard.html", context)
