from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.html import format_html

from accounts.permissions import role_required
from patients.models import ReferralRecord
from patients.services import get_patient_or_404
from pharmacy.models import Prescription

from . import services
from .models import Admission, AdmissionStatus, Bed, NursingCarePlan, Ward


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
            cause_of_death = request.POST.get("cause_of_death", "")
            death_cert = request.POST.get("death_certificate_issued") == "true"
            services.discharge(admission, request.user, request.POST.get("summary", ""), request.POST.get("disposition", "discharged"), cause_of_death, death_cert)
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
    ward_data = []
    for ward in wards:
        occupancy = services.ward_occupancy(ward)
        total = occupancy["total_beds"] or 1
        occupancy["occupancy_pct"] = round((occupancy["occupied_beds"] / total) * 100, 1)
        ward_data.append((ward, occupancy))
    admissions = services.active_admissions()
    total_beds = sum(ward.bed_count for ward in wards)
    occupied_beds = sum(item[1]["occupied_beds"] for item in ward_data)
    available_beds = max(total_beds - occupied_beds, 0)
    ward_chart = {
        "labels": [ward.name for ward, _ in ward_data],
        "occupied": [data["occupied_beds"] for _, data in ward_data],
        "capacity": [data["total_beds"] for _, data in ward_data],
    }
    return render(
        request,
        "inpatient/dashboard.html",
        {
            "ward_data": ward_data,
            "admissions": admissions,
            "ward_total": wards.count(),
            "bed_total": total_beds,
            "occupied_beds": occupied_beds,
            "available_beds": available_beds,
            "occupancy_rate": round((occupied_beds / total_beds) * 100, 1) if total_beds else 0,
            "ward_chart": ward_chart,
            "recent_admissions": admissions[:8],
        },
    )


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
    return HttpResponse(format_html('<select name="bed" class="w-full rounded-lg border-gray-200 text-sm"><option value="">- Assign later -</option>{}</select>', options))


# ── MAR (§8.1.4(g)) ─────────────────────────────────────────────────────


@role_required("Nurse", "Clinician", "Admin")
def mar_entry(request, admission_id):
    admission = get_object_or_404(Admission.objects.select_related("patient"), pk=admission_id, status=AdmissionStatus.ACTIVE)
    if request.method == "POST":
        prescription_id = request.POST.get("prescription")
        prescription = get_object_or_404(Prescription, pk=prescription_id, patient=admission.patient)
        dose = request.POST.get("dose", "").strip()
        route = request.POST.get("route", "")
        site = request.POST.get("site", "")
        notes = request.POST.get("notes", "")
        if not dose or not route:
            messages.error(request, "Dose and route are required.")
        else:
            from . import services as svc
            svc.record_administration(admission, prescription, request.user, dose, route, site, notes)
            messages.success(request, "Administration recorded.")
            return redirect(reverse("inpatient:admission_detail", args=[admission.pk]))
    from pharmacy.models import Prescription as Rx
    active_rxs = Rx.objects.filter(patient=admission.patient, status__in=["prescribed", "approved", "dispensed"])
    return render(request, "inpatient/mar_entry.html", {"admission": admission, "prescriptions": active_rxs})


# ── Nursing Care Plans (§8.1.4(e)) ──────────────────────────────────────


@role_required("Nurse", "Clinician", "Admin")
def care_plan_list(request, admission_id):
    admission = get_object_or_404(Admission.objects.select_related("patient"), pk=admission_id)
    plans = admission.care_plans.all().select_related("created_by", "evaluated_by")
    return render(request, "inpatient/care_plan_list.html", {"admission": admission, "plans": plans})


@role_required("Nurse", "Clinician", "Admin")
def care_plan_create(request, admission_id):
    admission = get_object_or_404(Admission.objects.select_related("patient"), pk=admission_id, status=AdmissionStatus.ACTIVE)
    if request.method == "POST":
        problem = request.POST.get("problem", "").strip()
        goal = request.POST.get("goal", "").strip()
        interventions = request.POST.get("interventions", "").strip()
        if not problem or not goal:
            messages.error(request, "Problem and goal are required.")
        else:
            from . import services as svc
            svc.create_care_plan(admission, request.user, problem, goal, interventions)
            messages.success(request, "Care plan created.")
            return redirect(reverse("inpatient:care_plan_list", args=[admission.pk]))
    return render(request, "inpatient/care_plan_form.html", {"admission": admission})


@role_required("Nurse", "Clinician", "Admin")
def care_plan_evaluate(request, pk):
    plan = get_object_or_404(NursingCarePlan, pk=pk)
    if request.method == "POST":
        evaluation = request.POST.get("evaluation", "").strip()
        status = request.POST.get("goal_status", "")
        if not evaluation:
            messages.error(request, "Evaluation is required.")
        else:
            from . import services as svc
            svc.evaluate_care_plan(plan, request.user, evaluation, status)
            messages.success(request, "Care plan evaluated.")
    return redirect(reverse("inpatient:care_plan_list", args=[plan.admission.pk]))


# ── Fluid Balance (§8.1.4(f)) ──────────────────────────────────────────


@role_required("Nurse", "Clinician", "Admin")
def fluid_balance(request, admission_id):
    admission = get_object_or_404(Admission.objects.select_related("patient"), pk=admission_id)
    if request.method == "POST":
        fluid_type = request.POST.get("fluid_type", "")
        volume = request.POST.get("volume_ml", "")
        if not fluid_type or not volume:
            messages.error(request, "Fluid type and volume are required.")
        else:
            from . import services as svc
            svc.record_fluid(admission, request.user, fluid_type, int(volume))
            messages.success(request, f"Recorded {volume}ml {fluid_type}.")
            return redirect(reverse("inpatient:fluid_balance", args=[admission.pk]))
    from . import services as svc
    summary = svc.fluid_balance_summary(admission)
    return render(request, "inpatient/fluid_balance.html", {"admission": admission, "summary": summary})


# ── Procedure Notes (§8.1.4(i)) ─────────────────────────────────────────


@role_required("Nurse", "Clinician", "Admin")
def procedure_note_create(request, admission_id):
    admission = get_object_or_404(Admission.objects.select_related("patient"), pk=admission_id, status=AdmissionStatus.ACTIVE)
    if request.method == "POST":
        procedure_name = request.POST.get("procedure_name", "").strip()
        findings = request.POST.get("findings", "").strip()
        if not procedure_name or not findings:
            messages.error(request, "Procedure name and findings are required.")
        else:
            from . import services as svc
            data = {
                "procedure_name": procedure_name,
                "indication": request.POST.get("indication", ""),
                "anaesthesia_type": request.POST.get("anaesthesia_type", ""),
                "findings": findings,
                "complications": request.POST.get("complications", ""),
                "outcome": request.POST.get("outcome", ""),
                "notes": request.POST.get("notes", ""),
            }
            svc.create_procedure_note(admission, request.user, **data)
            messages.success(request, "Procedure note recorded.")
            return redirect(reverse("inpatient:admission_detail", args=[admission.pk]))
    return render(request, "inpatient/procedure_note_form.html", {"admission": admission})


# ── Nursing Assessment (§8.1.6(a)) ──────────────────────────────────────


@role_required("Nurse", "Clinician", "Admin")
def nursing_assessment_list(request, admission_id):
    admission = get_object_or_404(Admission.objects.select_related("patient"), pk=admission_id)
    assessments = admission.nursing_assessments.all().select_related("assessed_by")
    return render(request, "inpatient/nursing_assessment_list.html", {"admission": admission, "assessments": assessments})


@role_required("Nurse", "Clinician", "Admin")
def nursing_assessment_create(request, admission_id):
    admission = get_object_or_404(Admission.objects.select_related("patient"), pk=admission_id, status=AdmissionStatus.ACTIVE)
    if request.method == "POST":
        note = request.POST.get("assessment_note", "").strip()
        if not note:
            messages.error(request, "Assessment note is required.")
        else:
            from . import services as svc
            # Collect problem rows: each row has problem_name and status
            problems = []
            problem_names = request.POST.getlist("problem_name[]")
            problem_statuses = request.POST.getlist("problem_status[]")
            for name, status in zip(problem_names, problem_statuses):
                name = name.strip()
                if name:
                    problems.append({"name": name, "status": status or "active"})
            svc.create_nursing_assessment(admission, request.user, note, problems)
            messages.success(request, "Assessment recorded.")
            return redirect(reverse("inpatient:nursing_assessment_list", args=[admission.pk]))
    return render(request, "inpatient/nursing_assessment_form.html", {"admission": admission})


# ── Referral (§8.1.2(g)) ────────────────────────────────────────────────


DEPARTMENT_CHOICES = [
    ("", "- Select department -"),
    ("Laboratory", "Laboratory"),
    ("Imaging", "Imaging / Radiology"),
    ("Pharmacy", "Pharmacy"),
    ("Theatre", "Theatre"),
    ("ICU", "ICU / HDU"),
    ("Ward", "Ward"),
    ("Physiotherapy", "Physiotherapy"),
    ("Other facility", "Other facility"),
]


@role_required("Nurse", "Clinician", "Admin")
def create_referral(request, patient_id):
    patient = get_patient_or_404(patient_id)
    if request.method == "POST":
        destination = request.POST.get("destination", "").strip()
        reason = request.POST.get("reason", "").strip()
        source = request.POST.get("source", "").strip() or "Ward"
        if not destination:
            messages.error(request, "Destination department is required.")
        else:
            ReferralRecord.objects.create(patient=patient, source=source, destination=destination, reason=reason)
            messages.success(request, f"Referral to {destination} created.")
            return redirect(reverse("patients:profile", args=[patient.pk]))
    return render(request, "inpatient/create_referral.html", {"patient": patient, "departments": DEPARTMENT_CHOICES})


@login_required
def referral_list(request, patient_id):
    patient = get_patient_or_404(patient_id)
    referrals = ReferralRecord.objects.filter(patient=patient).order_by("-created_at")
    return render(request, "inpatient/_referral_tab.html", {"patient": patient, "referrals": referrals})
