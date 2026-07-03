from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.permissions import role_required
from patients.services import get_patient_or_404

from . import services
from .forms import LabOrderForm, LabResultForm
from .models import LabOrder, LabResult


@login_required
def order_test(request, patient_id):
    patient = get_patient_or_404(patient_id)
    if request.method == "POST":
        form = LabOrderForm(request.POST)
        form.fields["encounter"].queryset = patient.encounters.all()
        if form.is_valid():
            order = services.create_order(patient, form.cleaned_data["test"], request.user, form.cleaned_data.get("encounter"))
            messages.success(request, "Lab order created.")
            return redirect(reverse("laboratory:collect", args=[order.pk]))
    else:
        form = LabOrderForm()
        form.fields["encounter"].queryset = patient.encounters.all()
    return render(request, "laboratory/order.html", {"form": form, "patient": patient})


@role_required("LabTech", "Admin")
def collect_specimen(request, pk):
    order = get_object_or_404(LabOrder, pk=pk)
    if request.method == "POST":
        order.mark_collected(request.user)
        messages.success(request, "Specimen collected.")
    return render(request, "laboratory/collect.html", {"order": order})


@role_required("LabTech", "Admin")
def enter_result(request, pk):
    order = get_object_or_404(LabOrder, pk=pk)
    if request.method == "POST":
        form = LabResultForm(request.POST)
        if form.is_valid():
            result = services.enter_result(order, form.cleaned_data, request.user)
            messages.success(request, "Lab result entered.")
            return redirect(reverse("laboratory:result_detail", args=[result.pk]))
    else:
        form = LabResultForm()
    return render(request, "laboratory/result_form.html", {"form": form, "order": order})


@login_required
def result_detail(request, pk):
    result = get_object_or_404(LabResult, pk=pk)
    return render(request, "laboratory/result_detail.html", {"result": result})


@role_required("LabTech", "Admin")
def verify_result(request, pk):
    result = get_object_or_404(LabResult, pk=pk)
    if request.method == "POST":
        try:
            services.verify_result(result, request.user)
        except ValueError as exc:
            raise PermissionDenied(str(exc))
        messages.success(request, "Lab result verified.")
    return redirect(reverse("laboratory:result_detail", args=[result.pk]))


@login_required
def patient_tab(request, patient_id):
    patient = get_patient_or_404(patient_id)
    return render(
        request,
        "laboratory/_patient_tab.html",
        {
            "patient": patient,
            "pending_orders": services.pending_orders_for(patient),
            "recent_results": services.recent_results_for(patient),
        },
    )


@role_required("LabTech", "Clinician", "Admin")
def workload(request):
    return render(request, "laboratory/workload.html", {"summary": services.workload_summary()})
