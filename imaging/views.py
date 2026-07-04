from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.permissions import role_required
from patients.services import get_patient_or_404

from . import services
from .forms import ImagingReportForm, ImagingRequestForm
from .models import ImagingReport, ImagingRequest


@login_required
def request_imaging(request, patient_id):
    patient = get_patient_or_404(patient_id)
    if request.method == "POST":
        form = ImagingRequestForm(request.POST)
        form.fields["encounter"].queryset = patient.encounters.all()
        if form.is_valid():
            imaging_request = services.create_request(patient, requested_by=request.user, **form.cleaned_data)
            messages.success(request, "Imaging request created.")
            if request.user.groups.filter(name__in=["Radiographer", "Admin"]).exists():
                return redirect(reverse("imaging:report", args=[imaging_request.pk]))
            return redirect(reverse("patients:profile", args=[patient.pk]))
    else:
        form = ImagingRequestForm()
        form.fields["encounter"].queryset = patient.encounters.all()
    return render(request, "imaging/request.html", {"form": form, "patient": patient})


@role_required("Radiographer", "Admin")
def enter_report(request, pk):
    imaging_request = get_object_or_404(ImagingRequest, pk=pk)
    if request.method == "POST":
        form = ImagingReportForm(request.POST)
        if form.is_valid():
            report = services.enter_report(imaging_request, form.cleaned_data, request.user)
            messages.success(request, "Imaging report entered.")
            return redirect(reverse("imaging:report_detail", args=[report.pk]))
    else:
        form = ImagingReportForm()
    return render(request, "imaging/report_form.html", {"form": form, "imaging_request": imaging_request})


@login_required
def patient_tab(request, patient_id):
    patient = get_patient_or_404(patient_id)
    return render(
        request,
        "imaging/_patient_tab.html",
        {
            "patient": patient,
            "pending_requests": services.pending_requests_for(patient),
            "recent_reports": services.recent_reports_for(patient),
        },
    )


@login_required
def report_detail(request, pk):
    report = get_object_or_404(ImagingReport, pk=pk)
    return render(request, "imaging/report_detail.html", {"report": report})


@role_required("Radiographer", "Clinician", "Admin")
def worklist(request):
    requests = ImagingRequest.objects.exclude(status="reported").select_related("patient", "modality")[:50]
    return render(request, "imaging/worklist.html", {"requests": requests})
