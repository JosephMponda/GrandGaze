from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.permissions import role_required
from patients.services import get_patient_or_404

from . import services
from .models import DialysisPrescription, VascularAccess


@login_required
def patient_tab(request, patient_id):
    patient = get_patient_or_404(patient_id)
    diagnosis = services.recent_diagnosis(patient)
    prescriptions = services.active_prescriptions_for(patient)
    return render(request, "dialysis/_patient_tab.html", {
        "patient": patient,
        "diagnosis": diagnosis,
        "prescriptions": prescriptions,
    })


@role_required("Clinician", "Nurse", "Admin")
def record_session(request, prescription_id):
    prescription = get_object_or_404(DialysisPrescription, pk=prescription_id, is_active=True)
    if request.method == "POST":
        pre = request.POST.get("pre_weight_kg")
        post = request.POST.get("post_weight_kg")
        complications = request.POST.get("complications", "")
        notes = request.POST.get("notes", "")
        if not pre or not post:
            messages.error(request, "Pre- and post-dialysis weight are required.")
        else:
            services.record_session(
                prescription, request.user,
                {"session_date": timezone.now().date(), "pre_weight_kg": pre,
                 "post_weight_kg": post, "complications": complications, "notes": notes},
            )
            messages.success(request, "Dialysis session recorded.")
            return redirect(reverse("dialysis:patient_tab", args=[prescription.patient_id]))
    return render(request, "dialysis/record_session.html", {
        "prescription": prescription,
    })


@login_required
def dashboard(request):
    today = timezone.now().date()
    sessions = (
        DialysisPrescription.objects.filter(is_active=True)
        .select_related("patient")
        .annotate(sessions_today=Count("sessions", filter=Q(sessions__session_date=today)))
    )
    counts = list(sessions)
    completed_today = sum(1 for rx in counts if rx.sessions_today)
    pending_today = max(len(counts) - completed_today, 0)
    completion_rate = round((completed_today / len(counts)) * 100, 1) if counts else 0
    access_labels = dict(VascularAccess.choices)
    access_counts = {}
    for rx in counts:
        access_counts[rx.vascular_access] = access_counts.get(rx.vascular_access, 0) + 1
    access_chart = {
        "labels": [access_labels.get(label, label) for label in access_counts.keys()],
        "values": [value for value in access_counts.values()],
    }
    return render(
        request,
        "dialysis/dashboard.html",
        {
            "counts": counts,
            "active_count": len(counts),
            "completed_today": completed_today,
            "pending_today": pending_today,
            "completion_rate": completion_rate,
            "access_chart": access_chart,
        },
    )
