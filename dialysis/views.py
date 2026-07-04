from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.permissions import role_required
from patients.services import get_patient_or_404

from . import services
from .models import DialysisPrescription


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
    sessions = DialysisPrescription.objects.filter(is_active=True).select_related("patient")
    counts = []
    for rx in sessions:
        done = rx.sessions.filter(session_date=today).count()
        counts.append({"prescription": rx, "sessions_today": done})
    return render(request, "dialysis/dashboard.html", {"counts": counts})
