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
from .models import Profile, Role, Task, TaskPriority, TaskStatus

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
    """Read-only audit viewer over django-simple-history records for all clinical models."""
    from patients.models import Patient
    from encounters.models import Encounter, AllergyRecord
    from vitals.models import VitalSignSet
    from laboratory.models import LabOrder, LabResult
    from imaging.models import ImagingRequest, ImagingReport
    from pharmacy.models import Prescription, DispensingRecord
    from billing.models import Invoice, Payment
    from emergency.models import TriageEncounter
    from dialysis.models import CKDDiagnosis, DialysisPrescription, DialysisSession
    from inpatient.models import Admission, WardRoundNote, MedicationAdministrationRecord, ProcedureNote

    model_filter = request.GET.get("model", "patient")
    limit = 200
    entries = []
    label = "Patient"

    def actor_name(h):
        if h.history_user:
            return h.history_user.get_full_name() or h.history_user.username
        return "System"

    def patient_name(obj):
        if obj is None:
            return "—"
        return getattr(obj, "full_name", str(obj))

    def patient_number(obj):
        if obj is None:
            return ""
        return getattr(obj, "patient_number", "")

    # ── Patients ──────────────────────────────────────────────────────────
    if model_filter == "patient":
        label = "Patient"
        for h in Patient.history.all().order_by("-history_date")[:limit]:
            entries.append(dict(date=h.history_date, type=h.history_type,
                title=patient_name(h),
                detail=f"Patient #{patient_number(h)}",
                actor=actor_name(h)))

    # ── Encounters ─────────────────────────────────────────────────────────
    elif model_filter == "encounter":
        label = "Encounter"
        for h in Encounter.history.select_related("patient", "clinician").order_by("-history_date")[:limit]:
            clinician = h.clinician.get_full_name() or h.clinician.username if h.clinician else "—"
            entries.append(dict(date=h.history_date, type=h.history_type,
                title=patient_name(h.patient),
                detail=f"{h.get_encounter_type_display()} — Clinician: {clinician}",
                actor=actor_name(h)))

    # ── Vitals ─────────────────────────────────────────────────────────────
    elif model_filter == "vitals":
        label = "Vitals"
        for h in VitalSignSet.history.select_related("patient", "recorded_by").order_by("-history_date")[:limit]:
            recorded = h.recorded_by.get_full_name() or h.recorded_by.username if h.recorded_by else "—"
            entries.append(dict(date=h.history_date, type=h.history_type,
                title=patient_name(h.patient),
                detail=f"Recorded by {recorded}",
                actor=actor_name(h)))

    # ── Lab Orders ─────────────────────────────────────────────────────────
    elif model_filter == "lab":
        label = "Lab"
        for h in LabOrder.history.select_related("patient", "ordered_by").order_by("-history_date")[:limit]:
            ordered = h.ordered_by.get_full_name() or h.ordered_by.username if h.ordered_by else "—"
            entries.append(dict(date=h.history_date, type=h.history_type,
                title=patient_name(h.patient),
                detail=f"Ordered by {ordered} — {h.status or '—'}",
                actor=actor_name(h)))

    # ── Lab Results ────────────────────────────────────────────────────────
    elif model_filter == "lab_result":
        label = "Lab Result"
        for h in LabResult.history.select_related("order__patient", "entered_by").order_by("-history_date")[:limit]:
            entered = h.entered_by.get_full_name() or h.entered_by.username if h.entered_by else "—"
            patient = h.order.patient if h.order and hasattr(h.order, "patient") else None
            entries.append(dict(date=h.history_date, type=h.history_type,
                title=patient_name(patient),
                detail=f"Entered by {entered} — {getattr(h, 'value', '')}",
                actor=actor_name(h)))

    # ── Imaging ────────────────────────────────────────────────────────────
    elif model_filter == "imaging":
        label = "Imaging"
        for h in ImagingRequest.history.select_related("patient", "requested_by").order_by("-history_date")[:limit]:
            requested = h.requested_by.get_full_name() or h.requested_by.username if h.requested_by else "—"
            entries.append(dict(date=h.history_date, type=h.history_type,
                title=patient_name(h.patient),
                detail=f"Requested by {requested} — {getattr(h, 'modality', '') or ''}",
                actor=actor_name(h)))

    # ── Prescriptions ──────────────────────────────────────────────────────
    elif model_filter == "prescription":
        label = "Prescription"
        for h in Prescription.history.select_related("patient", "prescribed_by").order_by("-history_date")[:limit]:
            prescriber = h.prescribed_by.get_full_name() or h.prescribed_by.username if h.prescribed_by else "—"
            entries.append(dict(date=h.history_date, type=h.history_type,
                title=patient_name(h.patient),
                detail=f"Prescribed by {prescriber}",
                actor=actor_name(h)))

    # ── Dispensing ─────────────────────────────────────────────────────────
    elif model_filter == "dispensing":
        label = "Dispensing"
        for h in DispensingRecord.history.select_related("prescription__patient", "dispensed_by").order_by("-history_date")[:limit]:
            dispensed = h.dispensed_by.get_full_name() or h.dispensed_by.username if h.dispensed_by else "—"
            patient = h.prescription.patient if h.prescription else None
            entries.append(dict(date=h.history_date, type=h.history_type,
                title=patient_name(patient),
                detail=f"Dispensed by {dispensed}",
                actor=actor_name(h)))

    # ── Billing / Invoices ─────────────────────────────────────────────────
    elif model_filter == "billing":
        label = "Billing"
        for h in Invoice.history.select_related("patient", "created_by").order_by("-history_date")[:limit]:
            creator = h.created_by.get_full_name() or h.created_by.username if h.created_by else "—"
            entries.append(dict(date=h.history_date, type=h.history_type,
                title=patient_name(h.patient),
                detail=f"Created by {creator} — {getattr(h, 'status', '') or ''}",
                actor=actor_name(h)))

    # ── Triage ─────────────────────────────────────────────────────────────
    elif model_filter == "triage":
        label = "Triage"
        for h in TriageEncounter.history.select_related("patient", "triaged_by").order_by("-history_date")[:limit]:
            triaged = h.triaged_by.get_full_name() or h.triaged_by.username if h.triaged_by else "—"
            entries.append(dict(date=h.history_date, type=h.history_type,
                title=patient_name(h.patient),
                detail=f"Triaged by {triaged}",
                actor=actor_name(h)))

    # ── Dialysis ───────────────────────────────────────────────────────────
    elif model_filter == "dialysis":
        label = "Dialysis"
        for h in DialysisSession.history.select_related("prescription__patient", "conducted_by").order_by("-history_date")[:limit]:
            conducted = h.conducted_by.get_full_name() or h.conducted_by.username if h.conducted_by else "—"
            patient = h.prescription.patient if h.prescription else None
            entries.append(dict(date=h.history_date, type=h.history_type,
                title=patient_name(patient),
                detail=f"Conducted by {conducted}",
                actor=actor_name(h)))

    # ── Inpatient / Admissions ─────────────────────────────────────────────
    elif model_filter == "admission":
        label = "Admission"
        for h in Admission.history.select_related("patient", "admitting_clinician").order_by("-history_date")[:limit]:
            clinician = h.admitting_clinician.get_full_name() or h.admitting_clinician.username if h.admitting_clinician else "—"
            entries.append(dict(date=h.history_date, type=h.history_type,
                title=patient_name(h.patient),
                detail=f"Admitted by {clinician} — {getattr(h, 'status', '') or ''}",
                actor=actor_name(h)))

    # ── Staff Profiles ─────────────────────────────────────────────────────
    elif model_filter == "profile":
        label = "Staff Profile"
        for h in Profile.history.select_related("user").order_by("-history_date")[:limit]:
            entries.append(dict(date=h.history_date, type=h.history_type,
                title=h.user.username if h.user else "—",
                detail=f"Role: {h.role}, Dept: {h.department or '—'}",
                actor=actor_name(h)))

    # ── Tasks ──────────────────────────────────────────────────────────────
    elif model_filter == "task":
        label = "Task"
        for h in Task.history.select_related("assigned_to", "assigned_by").order_by("-history_date")[:limit]:
            to_name = h.assigned_to.get_full_name() or h.assigned_to.username if h.assigned_to else "—"
            by_name = h.assigned_by.get_full_name() or h.assigned_by.username if h.assigned_by else "—"
            entries.append(dict(date=h.history_date, type=h.history_type,
                title=h.title,
                detail=f"Assigned to {to_name} by {by_name}",
                actor=actor_name(h)))

    total = len(entries)
    created = sum(1 for e in entries if e["type"] == "+")
    modified = sum(1 for e in entries if e["type"] == "~")
    deleted = sum(1 for e in entries if e["type"] == "-")

    return render(request, "accounts/audit_trail.html", {
        "history_entries": entries,
        "total_count": total,
        "created_count": created,
        "modified_count": modified,
        "deleted_count": deleted,
        "model_filter": model_filter,
        "model_label": label,
    })


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
    context = {
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
    if request.headers.get("HX-Request") == "true":
        return render(request, "accounts/_staff_directory.html", context)
    return render(request, "accounts/control_panel.html", context)


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
