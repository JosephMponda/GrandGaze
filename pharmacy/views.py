from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.permissions import role_required
from patients.services import get_patient_or_404

from . import services
from .forms import DispensingRecordForm, PrescriptionForm
from .models import Prescription, PrescriptionStatus
from .safety import check_prescription_safety


@login_required
def prescribe(request, patient_id):
    patient = get_patient_or_404(patient_id)
    warnings = []
    if request.method == "POST":
        form = PrescriptionForm(request.POST)
        form.fields["encounter"].queryset = patient.encounters.all()
        if form.is_valid():
            drug = form.cleaned_data["drug"]
            warnings = check_prescription_safety(patient, drug, form.cleaned_data.get("dose"))
            proceeding = form.cleaned_data.get("proceed_with_warnings")
            if warnings and not proceeding:
                form.fields["proceed_with_warnings"].initial = True
                return render(request, "pharmacy/prescribe.html", {"form": form, "patient": patient, "warnings": warnings})
            if warnings and not form.cleaned_data.get("safety_override_reason"):
                form.add_error("safety_override_reason", "Document the reason for proceeding after medication safety warnings.")
            else:
                data = form.cleaned_data.copy()
                data.pop("proceed_with_warnings", None)
                data.pop("drug", None)
                prescription, _ = services.prescribe(patient, drug, request.user, data)
                messages.success(request, "Prescription created.")
                return redirect(reverse("pharmacy:queue"))
    else:
        form = PrescriptionForm()
        form.fields["encounter"].queryset = patient.encounters.all()
    return render(request, "pharmacy/prescribe.html", {"form": form, "patient": patient, "warnings": warnings})


@role_required("Pharmacist", "Admin")
def queue(request):
    prescriptions = Prescription.objects.exclude(status__in=[PrescriptionStatus.DISPENSED, PrescriptionStatus.CANCELLED]).select_related("patient", "drug")[:50]
    return render(request, "pharmacy/queue.html", {"prescriptions": prescriptions})


@role_required("Pharmacist", "Admin")
def approve(request, pk):
    prescription = get_object_or_404(Prescription, pk=pk)
    if request.method == "POST":
        services.approve(prescription, request.user)
        messages.success(request, "Prescription approved.")
    return redirect(reverse("pharmacy:queue"))


@role_required("Pharmacist", "Admin")
def dispense(request, pk):
    prescription = get_object_or_404(Prescription, pk=pk)
    if request.method == "POST":
        form = DispensingRecordForm(request.POST)
        if form.is_valid():
            services.dispense(prescription, request.user, form.cleaned_data)
            messages.success(request, "Prescription dispensed.")
            return redirect(reverse("pharmacy:queue"))
    else:
        form = DispensingRecordForm()
    return render(request, "pharmacy/dispense.html", {"form": form, "prescription": prescription})


@login_required
def patient_tab(request, patient_id):
    patient = get_patient_or_404(patient_id)
    return render(request, "pharmacy/_patient_tab.html", {"patient": patient, "prescriptions": services.active_prescriptions_for(patient)})
