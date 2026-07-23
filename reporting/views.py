from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from encounters.models import Encounter
from laboratory.models import LabOrder
from imaging.models import ImagingRequest
from pharmacy.models import Prescription

from .models import AlertEvent
from .services import acknowledge


@login_required
def recent_alerts(request):
    alerts = AlertEvent.objects.filter(acknowledged_by__isnull=True).select_related("patient", "acknowledged_by")
    context = {
        "alerts": alerts,
        "critical_count": alerts.filter(severity="critical").count(),
        "warning_count": alerts.filter(severity="warning").count(),
        "info_count": alerts.filter(severity="info").count(),
    }
    return render(request, "reporting/recent_alerts.html", context)


@login_required
def acknowledge_alert(request, alert_id):
    alert = get_object_or_404(AlertEvent, pk=alert_id)
    acknowledge(alert, request.user)
    return redirect("reporting:recent_alerts")


@login_required
def analytics_dashboard(request):
    now = timezone.now()
    today = now.date()

    from patients.models import Patient

    alert_window = AlertEvent.objects.filter(raised_at__gte=now - timedelta(hours=4))
    severity_breakdown = alert_window.aggregate(
        critical=Count("pk", filter=Q(severity="critical")),
        warning=Count("pk", filter=Q(severity="warning")),
        info=Count("pk", filter=Q(severity="info")),
    )
    module_breakdown = {
        "labels": ["Patients", "Encounters", "Labs", "Imaging", "Meds", "Alerts"],
        "values": [
            Patient.objects.filter(created_at__date=today).count(),
            Encounter.objects.filter(signed_at__isnull=True).count(),
            LabOrder.objects.filter(status__in=["ordered", "specimen_collected", "in_progress"]).count(),
            ImagingRequest.objects.filter(status__in=["requested", "scheduled"]).count(),
            Prescription.objects.filter(status="prescribed").count(),
            AlertEvent.objects.filter(acknowledged_by__isnull=True).count(),
        ],
        "urls": [
            reverse("patients:register"),
            reverse("patients:register"),
            reverse("laboratory:workload"),
            reverse("imaging:worklist"),
            reverse("pharmacy:queue"),
            reverse("reporting:recent_alerts"),
        ],
    }

    context = {
        "patients_today": Patient.objects.filter(created_at__date=today).count(),
        "open_encounters": Encounter.objects.filter(signed_at__isnull=True).count(),
        "pending_labs": LabOrder.objects.filter(status__in=["ordered", "specimen_collected", "in_progress"]).count(),
        "pending_imaging": ImagingRequest.objects.filter(status__in=["requested", "scheduled"]).count(),
        "pending_prescriptions": Prescription.objects.filter(status="prescribed").count(),
        "unacknowledged_alerts": AlertEvent.objects.filter(acknowledged_by__isnull=True).count(),
        "critical_alerts_4h": AlertEvent.objects.filter(
            severity="critical",
            raised_at__gte=now - timedelta(hours=4),
        ).count(),
        "warning_count": severity_breakdown["warning"] or 0,
        "info_count": severity_breakdown["info"] or 0,
        "severity_chart": {
            "labels": ["Critical", "Warning", "Info"],
            "values": [
                severity_breakdown["critical"] or 0,
                severity_breakdown["warning"] or 0,
                severity_breakdown["info"] or 0,
            ],
        },
        "module_chart": module_breakdown,
        "recent_alerts": alert_window.select_related("patient").order_by("-raised_at")[:6],
    }
    return render(request, "reporting/analytics_dashboard.html", context)
