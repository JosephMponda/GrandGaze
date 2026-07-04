from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.permissions import role_required
from patients.services import get_patient_or_404

from . import services
from .forms import DispensingRecordForm, PrescriptionForm, StockAdjustForm
from .models import Prescription, PrescriptionStatus, StockLevel
from .safety import CriticalSafetyBlock, check_prescription_safety


@login_required
def prescribe(request, patient_id):
    patient = get_patient_or_404(patient_id)
    warnings = []
    blocked = False
    if request.method == "POST":
        form = PrescriptionForm(request.POST)
        form.fields["encounter"].queryset = patient.encounters.all()
        if form.is_valid():
            drug = form.cleaned_data["drug"]
            warnings = check_prescription_safety(patient, drug, form.cleaned_data.get("dose"))
            critical = [w for w in warnings if w.level == "critical"]
            proceeding = form.cleaned_data.get("proceed_with_warnings")
            if critical:
                # Critical warnings can never be bypassed from this form -
                # no override checkbox, no reason field, full stop.
                return render(request, "pharmacy/prescribe.html", {"form": form, "patient": patient, "warnings": warnings, "blocked": True})
            if warnings and not proceeding:
                form.fields["proceed_with_warnings"].initial = True
                return render(request, "pharmacy/prescribe.html", {"form": form, "patient": patient, "warnings": warnings})
            if warnings and not form.cleaned_data.get("safety_override_reason"):
                form.add_error("safety_override_reason", "Document the reason for proceeding after medication safety warnings.")
            else:
                data = form.cleaned_data.copy()
                data.pop("proceed_with_warnings", None)
                data.pop("drug", None)
                try:
                    prescription, _ = services.prescribe(patient, drug, request.user, data)
                except CriticalSafetyBlock as exc:
                    # Defense in depth: something changed the warning set
                    # (e.g. a new allergy recorded) between the check above
                    # and this write.
                    return render(request, "pharmacy/prescribe.html", {"form": form, "patient": patient, "warnings": exc.warnings, "blocked": True})
                messages.success(request, "Prescription created.")
                return redirect(reverse("patients:profile", args=[patient.pk]))
    else:
        form = PrescriptionForm()
        form.fields["encounter"].queryset = patient.encounters.all()
    return render(request, "pharmacy/prescribe.html", {"form": form, "patient": patient, "warnings": warnings, "blocked": blocked})


@role_required("Pharmacist", "Admin")
def queue(request):
    prescriptions = Prescription.objects.exclude(status__in=[PrescriptionStatus.DISPENSED, PrescriptionStatus.CANCELLED]).select_related("patient", "drug")[:50]
    drug_ids = [p.drug_id for p in prescriptions]
    stock_map = {s.drug_id: s for s in StockLevel.objects.filter(drug_id__in=drug_ids)}
    for p in prescriptions:
        p.stock = stock_map.get(p.drug_id)
    return render(request, "pharmacy/queue.html", {"prescriptions": prescriptions})


@login_required
def cancel(request, pk):
    prescription = get_object_or_404(Prescription, pk=pk)
    if request.method == "POST":
        services.cancel_prescription(prescription, request.user)
        messages.success(request, "Prescription cancelled.")
    return redirect(reverse("patients:profile", args=[prescription.patient_id]))


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
    stock_qty, in_stock = services.check_stock(prescription.drug)
    if request.method == "POST":
        if not in_stock:
            messages.error(request, f"{prescription.drug.generic_name} is out of stock.")
            return redirect(reverse("pharmacy:queue"))
        form = DispensingRecordForm(request.POST)
        if form.is_valid():
            services.dispense(prescription, request.user, form.cleaned_data)
            services.adjust_stock(prescription.drug, -1, request.user, f"dispensed #{prescription.pk}")
            messages.success(request, "Prescription dispensed.")
            return redirect(reverse("pharmacy:queue"))
    else:
        form = DispensingRecordForm()
    return render(request, "pharmacy/dispense.html", {"form": form, "prescription": prescription, "stock_qty": stock_qty, "in_stock": in_stock})


@login_required
def patient_tab(request, patient_id):
    patient = get_patient_or_404(patient_id)
    return render(request, "pharmacy/_patient_tab.html", {"patient": patient, "prescriptions": services.active_prescriptions_for(patient)})


@role_required("Pharmacist", "Admin")
def stock_adjust(request):
    if request.method == "POST":
        form = StockAdjustForm(request.POST)
        if form.is_valid():
            drug = form.cleaned_data["drug"]
            services.adjust_stock(
                drug, form.cleaned_data["quantity"], request.user, form.cleaned_data.get("note", "")
            )
            messages.success(request, f"Added {form.cleaned_data['quantity']} units of {drug.generic_name}.")
            return redirect(reverse("pharmacy:stock"))
    else:
        form = StockAdjustForm()
    stock_levels = StockLevel.objects.select_related("drug").all()
    return render(request, "pharmacy/stock.html", {"form": form, "stock_levels": stock_levels})
