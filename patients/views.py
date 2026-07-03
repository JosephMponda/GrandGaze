from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from . import services
from .forms import PatientRegistrationForm


@login_required
def register_patient(request):
    if request.method == "POST":
        form = PatientRegistrationForm(request.POST)
        confirmed_candidate_id = request.POST.get("confirmed_not_duplicate_of")
        if form.is_valid():
            duplicates = services.check_possible_duplicate(form.cleaned_data)
            confirmed_candidate = duplicates.filter(pk=confirmed_candidate_id).first() if confirmed_candidate_id else None
            remaining_duplicates = duplicates.exclude(pk=confirmed_candidate.pk) if confirmed_candidate else duplicates
            if remaining_duplicates.exists() or (confirmed_candidate_id and not confirmed_candidate):
                # Block silent creation — surface candidates, require explicit confirmation.
                return render(
                    request,
                    "patients/_duplicate_warning.html",
                    {"form": form, "candidates": remaining_duplicates[:10]},
                )
            patient = services.register_patient(form.cleaned_data, registered_by=request.user)
            if confirmed_candidate:
                services.confirm_not_duplicate(patient, confirmed_candidate, confirmed_by=request.user)
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
    tabs = [
        {"id": "encounters", "label": "Visits & Encounters", "badge": patient.encounters.count()},
        {"id": "vitals", "label": "Vitals", "badge": patient.vital_sign_sets.count()},
        {"id": "labs", "label": "Labs", "badge": patient.lab_orders.count()},
        {"id": "imaging", "label": "Imaging", "badge": patient.imaging_requests.count()},
        {"id": "prescriptions", "label": "Prescriptions", "badge": patient.prescriptions.count()},
        {"id": "billing", "label": "Billing", "badge": patient.invoices.count()},
        {"id": "triage", "label": "Triage", "badge": patient.triage_encounters.count()},
        {"id": "dialysis", "label": "Dialysis", "badge": patient.dialysis_prescriptions.count()},
        {"id": "inpatient", "label": "Admissions", "badge": patient.admissions.count()},
    ]
    return render(request, "patients/profile.html", {"patient": patient, "tabs": tabs})
