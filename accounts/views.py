from django.contrib import messages
from django.contrib.auth import get_user_model, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse, reverse_lazy
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
from .forms import StaffUserForm, StaffProfileForm
from .models import Profile, Role, Task, TaskStatus

User = get_user_model()


def logout_view(request):
    if request.method == "POST":
        auth_logout(request)
    return redirect("accounts:landing")


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

    activity_labels = ["Encounters", "Labs", "Imaging", "Meds", "Alerts"]
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
    alert_4h_critical = alert_severity_breakdown["critical"] or 0
    alert_4h_warning = alert_severity_breakdown["warning"] or 0
    alert_4h_info = alert_severity_breakdown["info"] or 0

    tasks = Task.objects.filter(assigned_to=request.user).exclude(status__in=["completed", "cancelled"])
    task_count = tasks.count()
    context = {
        "widgets": widgets_for_user(request.user),
        "tasks": tasks,
        "task_count": task_count,
        "patients_today": Patient.objects.filter(created_at__date=today).count(),
        "open_encounters": open_encounters,
        "pending_labs": pending_labs,
        "pending_imaging": pending_imaging,
        "pending_prescriptions": pending_prescriptions,
        "unacknowledged_alerts": unacknowledged_alerts,
        "critical_alerts_4h": critical_alerts_4h,
        "warning_count": alert_4h_warning,
        "info_count": alert_4h_info,
        "recent_alerts": AlertEvent.objects.select_related("patient").order_by("-raised_at")[:5],
        "activity_chart": {
            "labels": activity_labels,
            "values": activity_values,
            "max": activity_max,
            "urls": [
                reverse("encounters:open"),
                reverse("laboratory:workload"),
                reverse("imaging:worklist"),
                reverse("pharmacy:queue"),
                reverse("reporting:recent_alerts"),
            ],
        },
        "severity_chart": {
            "labels": ["Critical", "Warning", "Info"],
            "values": [
                alert_4h_critical,
                alert_4h_warning,
                alert_4h_info,
            ],
        },
    }
    return render(request, "accounts/dashboard.html", context)

def landing_page(request):
    """Public landing page for the EMR system."""
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    return render(request, 'landing.html')

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
    role_filter = request.GET.get("role", "")
    users = User.objects.select_related("profile").all().order_by("username")
    if role_filter and role_filter in dict(Role.choices):
        users = users.filter(profile__role=role_filter)

    wards = Ward.objects.all().order_by("name")
    bed_total = Bed.objects.count()
    occupied_beds = Bed.objects.filter(is_occupied=True).count()
    role_distribution = (
        User.objects.filter(profile__isnull=False)
        .values("profile__role")
        .annotate(total=Count("pk"))
        .order_by("profile__role")
    )
    role_dist_items = list(role_distribution)
    return render(
        request,
        "accounts/control_panel.html",
        {
            "users": users,
            "wards": wards,
            "user_total": User.objects.count(),
            "ward_total": wards.count(),
            "bed_total": bed_total,
            "occupied_beds": occupied_beds,
            "available_beds": max(bed_total - occupied_beds, 0),
            "role_filter": role_filter,
            "role_distribution": {
                "labels": [dict(Role.choices).get(item["profile__role"], item["profile__role"]) for item in role_dist_items],
                "values": [item["total"] for item in role_dist_items],
                "roles": [item["profile__role"] for item in role_dist_items],
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


@login_required
def user_detail(request, pk):
    user = get_object_or_404(User.objects.select_related("profile"), pk=pk)
    if not request.user.profile or request.user.profile.role not in ("Admin", "ICT"):
        if request.user.pk != user.pk:
            return redirect("accounts:user_detail", pk=request.user.pk)
    return render(request, "accounts/user_detail.html", {"staff_user": user})


@login_required
def edit_user(request, pk):
    user = get_object_or_404(User.objects.select_related("profile"), pk=pk)
    if not request.user.profile or request.user.profile.role not in ("Admin", "ICT"):
        if request.user.pk != user.pk:
            return redirect("accounts:user_detail", pk=request.user.pk)
    profile = user.profile
    form = StaffProfileForm(request.POST or None, request.FILES or None, instance=profile, user=user)
    if request.method == "POST" and form.is_valid():
        form.save()
        display_name = user.get_full_name() or user.username
        messages.success(request, f"Profile for {display_name} updated.")
        return redirect("accounts:user_detail", pk=user.pk)
    return render(request, "accounts/edit_user.html", {"form": form, "staff_user": user})


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


@role_required("Admin", "ICT")
def assign_task(request):
    """Assign a task/duty to a staff user."""
    users = User.objects.filter(is_active=True).select_related("profile").order_by("username")
    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description", "")
        assigned_to_id = request.POST.get("assigned_to")
        patient_raw = request.POST.get("patient", "").strip()
        priority = request.POST.get("priority", "medium")
        due_date = request.POST.get("due_date")
        patient = None
        if patient_raw:
            try:
                patient = Patient.objects.get(pk=patient_raw)
            except (Patient.DoesNotExist, ValueError):
                try:
                    patient = Patient.objects.get(patient_number__iexact=patient_raw)
                except Patient.DoesNotExist:
                    pass
        if title and assigned_to_id and due_date:
            Task.objects.create(
                title=title,
                description=description,
                assigned_to_id=assigned_to_id,
                assigned_by=request.user,
                patient=patient,
                priority=priority,
                due_date=due_date,
            )
            messages.success(request, "Task assigned.")
            return redirect("accounts:control_panel")
        messages.error(request, "Title, assignee, and due date are required.")
    today = timezone.localdate()
    return render(request, "accounts/assign_task.html", {"users": users, "today": today.isoformat()})


@login_required
def update_task_status(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if task.assigned_to != request.user:
        if not request.user.profile or request.user.profile.role not in ("Admin", "ICT"):
            return redirect("accounts:dashboard")
    new_status = request.POST.get("status", "")
    if new_status in dict(TaskStatus.choices):
        task.status = new_status
        task.save()
        messages.success(request, f"Task marked as {task.get_status_display().lower()}.")
    return redirect(request.META.get("HTTP_REFERER", "accounts:dashboard"))
