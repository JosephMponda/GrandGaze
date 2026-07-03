from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from encounters.services import get_open_encounter
from patients.services import get_patient_or_404

from . import services
from .forms import VitalSignSetForm


@login_required
def vitals_entry(request, patient_id):
    patient = get_patient_or_404(patient_id)
    encounter = get_open_encounter(patient)
    if encounter is None:
        messages.error(request, "Open an encounter for this patient before recording vitals.")
        return redirect(reverse("encounters:new", args=[patient.pk]))

    if request.method == "POST":
        form = VitalSignSetForm(request.POST)
        if form.is_valid():
            vitals = services.record_vitals(encounter, request.user, form.cleaned_data)
            # HTMX partial: EWS badge + trend sparkline, same request/response cycle.
            return render(request, "vitals/_result.html", {"vitals": vitals, "trend": services.vitals_trend(patient)})
    else:
        form = VitalSignSetForm()
    return render(request, "vitals/entry.html", {"form": form, "patient": patient})


@login_required
def patient_vitals_tab(request, patient_id):
    """HTMX partial plugged into Engineer A's patient profile template."""
    patient = get_patient_or_404(patient_id)
    trend = services.vitals_trend(patient)
    return render(request, "vitals/_patient_tab.html", {"patient": patient, "trend": trend})
