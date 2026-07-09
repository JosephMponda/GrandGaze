from django.contrib import messages
from django.contrib.auth import get_user_model, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from patients.models import Patient
from inpatient.models import Ward, Bed
from encounters.models import Encounter
from laboratory.models import LabOrder
from imaging.models import ImagingRequest
from pharmacy.models import Prescription
from reporting.models import AlertEvent
from .dashboard_widgets import widgets_for_user
from .permissions import role_required
from .forms import StaffUserForm
from .models import Role

User = get_user_model()


def logout_view(request):
    if request.method == "POST":
        auth_logout(request)
    return redirect("accounts:login")


@login_required
def dashboard(request):
    """Role-aware landing page - MVP requirement (brief §12)."""
    now = timezone.now()
    today = now.date()
    open_encounters = Encounter.objects.filter(signed_at__isnull=True).count()
    pending_labs = LabOrder.objects.filter(status__in=["ordered", "specimen_collected", "in_progress"]).count()
    pending_imaging = ImagingRequest.objects.filter(status__in=["requested", "scheduled"]).count()
    pending_prescriptions = Prescription.objects.filter(status="prescribed").count()
    unacknowledged_alerts = AlertEvent.objects.filter(acknowledged_by__isnull=True).count()
    critical_alerts_4h = AlertEvent.objects.filter(
        severity="critical",
        raised_at__gte=now - timedelta(hours=4),
    ).count()

    activity_labels = ["Encounters", "Labs", "Imaging", "Rx", "Alerts"]
    activity_values = [
        open_encounters,
        pending_labs,
        pending_imaging,
        pending_prescriptions,
        unacknowledged_alerts,
    ]
    activity_max = max(activity_values) if any(activity_values) else 1

    alert_severity_breakdown = AlertEvent.objects.filter(raised_at__gte=now - timedelta(hours=4)).aggregate(
        critical=Count("pk", filter=Q(severity="critical")),
        warning=Count("pk", filter=Q(severity="warning")),
        info=Count("pk", filter=Q(severity="info")),
    )

    context = {
        "widgets": widgets_for_user(request.user),
        "patients_today": Patient.objects.filter(created_at__date=today).count(),
        "open_encounters": open_encounters,
        "pending_labs": pending_labs,
        "pending_imaging": pending_imaging,
        "pending_prescriptions": pending_prescriptions,
        "unacknowledged_alerts": unacknowledged_alerts,
        "critical_alerts_4h": critical_alerts_4h,
        "recent_alerts": AlertEvent.objects.select_related("patient").order_by("-raised_at")[:5],
        "activity_chart": {
            "labels": activity_labels,
            "values": activity_values,
            "max": activity_max,
        },
        "severity_chart": {
            "labels": ["Critical", "Warning", "Info"],
            "values": [
                alert_severity_breakdown["critical"] or 0,
                alert_severity_breakdown["warning"] or 0,
                alert_severity_breakdown["info"] or 0,
            ],
        },
    }
    return render(request, "accounts/dashboard.html", context)


@role_required("Admin", "ICT")
def audit_trail(request):
    """Read-only audit viewer over django-simple-history records.
    Satisfies brief §19.4 as a visible feature, not just a DB table.
    """
    patient_history = Patient.history.all().order_by("-history_date")[:200]
    
    # Calculate counts using database aggregation
    total_count = patient_history.count()
    
    # Count by history type
    history_counts = patient_history.aggregate(
        created_count=Count('pk', filter=Q(history_type='+')),
        modified_count=Count('pk', filter=Q(history_type='~')),
        deleted_count=Count('pk', filter=Q(history_type='-')),
    )
    
    context = {
        "patient_history": patient_history,
        "total_count": total_count,
        "created_count": history_counts['created_count'],
        "modified_count": history_counts['modified_count'],
        "deleted_count": history_counts['deleted_count'],
    }
    
    return render(request, "accounts/audit_trail.html", context)


@role_required("Admin", "ICT")
def control_panel(request):
    """System configuration and user management dashboard."""
    users = User.objects.select_related("profile").all().order_by("username")
    wards = Ward.objects.all().order_by("name")
    bed_total = Bed.objects.count()
    occupied_beds = Bed.objects.filter(is_occupied=True).count()
    role_distribution = (
        User.objects.filter(profile__isnull=False)
        .values("profile__role")
        .annotate(total=Count("pk"))
        .order_by("profile__role")
    )
    return render(
        request,
        "accounts/control_panel.html",
        {
            "users": users,
            "wards": wards,
            "user_total": users.count(),
            "ward_total": wards.count(),
            "bed_total": bed_total,
            "occupied_beds": occupied_beds,
            "available_beds": max(bed_total - occupied_beds, 0),
            "role_distribution": {
                "labels": [dict(Role.choices).get(item["profile__role"], item["profile__role"]) for item in role_distribution],
                "values": [item["total"] for item in role_distribution],
            },
            "ward_rows": [
                {
                    "name": ward.name,
                    "department": ward.department or "General Medicine",
                    "beds": ward.bed_count,
                    "occupied": ward.beds.filter(is_occupied=True).count(),
                    "occupied_pct": round((ward.beds.filter(is_occupied=True).count() / ward.bed_count) * 100) if ward.bed_count else 0,
                }
                for ward in wards
            ],
        }
    )


@role_required("Admin", "ICT")
def add_user(request):
    """Create new EMR staff user and profile."""
    if request.method == "POST":
        form = StaffUserForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "New staff user account created.")
            return redirect(reverse("accounts:control_panel"))
    else:
        form = StaffUserForm()
    return render(request, "accounts/add_user.html", {"form": form})


@role_required("Admin", "ICT")
@transaction.atomic
def add_ward(request):
    """Create new ward and dynamically populate its beds."""
    if request.method == "POST":
        name = request.POST.get("name")
        department = request.POST.get("department", "")
        bed_count = request.POST.get("bed_count", "0")
        try:
            bed_count_int = int(bed_count)
            if not name or bed_count_int <= 0:
                messages.error(request, "Ward name and a valid bed count are required.")
            else:
                ward = Ward.objects.create(name=name, department=department, bed_count=bed_count_int)
                for i in range(1, bed_count_int + 1):
                    Bed.objects.create(ward=ward, label=f"Bed {i}")
                messages.success(request, f"Ward '{name}' created with {bed_count_int} beds.")
                return redirect(reverse("accounts:control_panel"))
        except ValueError:
            messages.error(request, "Invalid bed count value.")
    return render(request, "accounts/add_ward.html")
