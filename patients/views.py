from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from . import services
from .forms import PatientRegistrationForm
from .models import Patient


@login_required
def register_patient(request):
    if request.method == "POST":
        form = PatientRegistrationForm(request.POST)
        confirmed_candidate_id = request.POST.get("confirmed_not_duplicate_of")
        if form.is_valid():
            duplicates = services.check_possible_duplicate(form.cleaned_data)
            duplicates = duplicates.exclude(pk=confirmed_candidate_id) if confirmed_candidate_id else duplicates
            if duplicates.exists() and not confirmed_candidate_id:
                # Block silent creation - surface candidates, require explicit confirmation.
                return render(
                    request,
                    "patients/_duplicate_warning.html",
                    {"form": form, "candidates": duplicates},
                )
            patient = services.register_patient(form.cleaned_data, registered_by=request.user)
            if confirmed_candidate_id:
                candidate = get_object_or_404(Patient, pk=confirmed_candidate_id)
                services.confirm_not_duplicate(patient, candidate, confirmed_by=request.user)
            messages.success(request, f"Patient {patient.patient_number} registered.")
            return redirect(reverse("patients:profile", args=[patient.pk]))
    else:
        form = PatientRegistrationForm()
    return render(request, "patients/register.html", {"form": form})


@login_required
def search_patients(request):
    """HTMX live-search partial (search-as-you-type)."""
    query = request.GET.get("q", "")
    results = services.search_patients(query)
    return render(request, "patients/_search_results.html", {"results": results, "query": query})


@login_required
def patient_profile(request, pk):
    patient = services.get_patient_or_404(pk)
    return render(request, "patients/profile.html", {"patient": patient})
