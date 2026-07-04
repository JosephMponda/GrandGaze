from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.html import format_html

from accounts.permissions import role_required
from patients.services import get_patient_or_404

from . import services
from .models import Admission, AdmissionStatus, Bed, Ward


@role_required("Clinician", "Nurse", "Admin")
def admit(request, patient_id):
    patient = get_patient_or_404(patient_id)
    if request.method == "POST":
        diagnosis = request.POST.get("diagnosis", "")
        ward_id = request.POST.get("ward")
        bed_id = request.POST.get("bed")
        if not diagnosis:
            messages.error(request, "Admission diagnosis is required.")
        else:
            bed = get_object_or_404(Bed, pk=bed_id) if bed_id else None
            admission = services.admit_patient(patient, request.user, diagnosis, bed=bed)
            messages.success(request, f"{patient.full_name} admitted.")
            return redirect(reverse("inpatient:admission_detail", args=[admission.pk]))
    wards = Ward.objects.all()
    return render(request, "inpatient/admit.html", {"patient": patient, "wards": wards})


@login_required
def admission_detail(request, pk):
    admission = get_object_or_404(Admission.objects.select_related("patient", "bed__ward", "encounter"), pk=pk)
    wards = Ward.objects.all()
    available = services.available_beds().exclude(pk=admission.bed_id) if admission.bed else services.available_beds()
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "transfer":
            target_bed = get_object_or_404(Bed, pk=request.POST.get("bed"))
            services.transfer_patient(admission, target_bed, request.POST.get("reason", ""))
            messages.success(request, "Patient transferred.")
            return redirect(reverse("inpatient:admission_detail", args=[admission.pk]))
        elif action == "discharge":
            services.discharge(admission, request.user, request.POST.get("summary", ""), request.POST.get("disposition", "discharged"))
            messages.success(request, "Patient discharged.")
            return redirect(reverse("inpatient:admission_detail", args=[admission.pk]))
        elif action == "ward_round":
            note = request.POST.get("note", "")
            if note:
                services.add_ward_round_note(admission, request.user, note, request.POST.get("diagnosis_update", ""), request.POST.get("plan_update", ""))
                messages.success(request, "Ward round note added.")
            return redirect(reverse("inpatient:admission_detail", args=[admission.pk]))
    return render(request, "inpatient/admission_detail.html", {"admission": admission, "wards": wards, "available": available})


@login_required
def ward_dashboard(request, ward_id):
    ward = get_object_or_404(Ward, pk=ward_id)
    beds = Bed.objects.filter(ward=ward).select_related("current_admission__patient")
    occupancy = services.ward_occupancy(ward)
    return render(request, "inpatient/ward.html", {"ward": ward, "beds": beds, "occupancy": occupancy})


@login_required
def dashboard(request):
    wards = Ward.objects.all()
    ward_data = [(w, services.ward_occupancy(w)) for w in wards]
    admissions = services.active_admissions()
    return render(request, "inpatient/dashboard.html", {"ward_data": ward_data, "admissions": admissions})


@login_required
def patient_tab(request, patient_id):
    patient = get_patient_or_404(patient_id)
    admissions = Admission.objects.filter(patient=patient).select_related("bed__ward").order_by("-admitted_at")
    return render(request, "inpatient/_patient_tab.html", {"patient": patient, "admissions": admissions})


@login_required
def beds_for_ward(request):
    ward_id = request.GET.get("ward")
    beds = Bed.objects.filter(ward_id=ward_id, is_occupied=False) if ward_id else Bed.objects.none()
    options = "".join(format_html('<option value="{}">{}</option>', b.pk, b.label) for b in beds)
    return HttpResponse(format_html('<select name="bed" class="w-full rounded-lg border-gray-200 text-sm"><option value="">— Assign later —</option>{}</select>', options))
