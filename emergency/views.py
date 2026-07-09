from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from patients.services import get_patient_or_404

from .forms import RapidRegisterForm, TriageForm
from .models import TriageEncounter
from . import services


@login_required
def triage_patient(request, patient_id):
    patient = get_patient_or_404(patient_id)
    if request.method == "POST":
        form = TriageForm(request.POST)
        if form.is_valid():
            form.save(patient=patient, triaged_by=request.user)
            messages.success(request, f"Triage recorded for {patient.first_name} {patient.last_name}.")
            return redirect(reverse("emergency:queue"))
    else:
        form = TriageForm()
    return render(request, "emergency/triage_form.html", {"form": form, "patient": patient})


@login_required
def rapid_register(request):
    if request.method == "POST":
        form = RapidRegisterForm(request.POST)
        if form.is_valid():
            patient, triage = form.save(registered_by=request.user)
            messages.success(request, f"Rapid registration complete for {patient.first_name} {patient.last_name}.")
            return redirect(reverse("emergency:queue"))
    else:
        form = RapidRegisterForm()
    return render(request, "emergency/rapid_register.html", {"form": form})


@login_required
def queue(request):
    triages = services.triage_queue()
    category_counts = {}
    for triage in triages:
        category_counts[triage.triage_category] = category_counts.get(triage.triage_category, 0) + 1
    category_labels = dict(TriageEncounter._meta.get_field("triage_category").choices)
    triage_chart = {
        "labels": [category_labels.get(category, category) for category in category_counts.keys()],
        "values": list(category_counts.values()),
    }
    return render(
        request,
        "emergency/queue.html",
        {
            "triages": triages,
            "waiting_count": len(triages),
            "urgent_count": category_counts.get("immediate", 0) + category_counts.get("emergency", 0),
            "triage_chart": triage_chart,
        },
    )


@login_required
def resolve(request, pk):
    triage = get_object_or_404(TriageEncounter, pk=pk)
    if request.method == "POST":
        outcome = request.POST.get("outcome")
        note = request.POST.get("disposition_note", "")
        if outcome:
            services.resolve_triage(triage, outcome, note)
            messages.success(request, f"Triage resolved: {triage.get_outcome_display()}.")
        return redirect(reverse("emergency:queue"))
    return render(request, "emergency/resolve.html", {"triage": triage})


@login_required
def patient_tab(request, patient_id):
    patient = get_patient_or_404(patient_id)
    triages = services.triage_history_for(patient)
    return render(request, "emergency/_patient_tab.html", {"patient": patient, "triages": triages})
