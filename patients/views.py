from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from . import services
from .forms import PatientRegistrationForm
from .models import Patient


@login_required
def patient_list(request):
    today = timezone.now().date()
    patients_today_count = Patient.objects.filter(created_at__date=today).count()
    query = request.GET.get("q", "")
    date_from = request.GET.get("date_from", "")
    time_to = request.GET.get("time_to", "")

    patients = Patient.objects.all()
    if query:
        patients = patients.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(patient_number__icontains=query)
        )
    if date_from:
        patients = patients.filter(created_at__date__gte=date_from)
    if time_to:
        patients = patients.filter(created_at__time__lte=time_to)

    return render(request, "patients/list.html", {
        "patients": patients,
        "patients_today_count": patients_today_count,
        "query": query,
        "date_from": date_from,
        "time_to": time_to,
    })


@login_required
def register_patient(request):
    if request.method == "POST":
        form = PatientRegistrationForm(request.POST)
        if request.POST.get("back_to_edit"):
            # User hit "Go Back & Edit Form" from the duplicate-warning screen.
            # Re-render with the same bound form so nothing they already typed
            # is lost - a plain GET here would silently discard the submission.
            return render(request, "patients/register.html", {"form": form})
        confirmed_candidate_id = request.POST.get("confirmed_not_duplicate_of")
        if form.is_valid():
            duplicates = services.check_possible_duplicate(form.cleaned_data)
            confirmed_candidate = duplicates.filter(pk=confirmed_candidate_id).first() if confirmed_candidate_id else None
            remaining_duplicates = duplicates.exclude(pk=confirmed_candidate.pk) if confirmed_candidate else duplicates
            if remaining_duplicates.exists() or (confirmed_candidate_id and not confirmed_candidate):
                # Block silent creation - surface candidates, require explicit confirmation.
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
def edit_patient(request, pk):
    patient = services.get_patient_or_404(pk)
    if request.method == "POST":
        form = PatientRegistrationForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, "Patient updated.")
            return redirect(reverse("patients:profile", args=[patient.pk]))
    else:
        form = PatientRegistrationForm(instance=patient)
    return render(request, "patients/register.html", {"form": form, "editing": True, "patient": patient})


@login_required
def patient_profile(request, pk):
    patient = services.get_patient_or_404(pk)
    vitals = list(patient.vital_sign_sets.select_related("ews").order_by("-recorded_at")[:6])
    vitals.reverse()
    vitals_chart = {
        "labels": [v.recorded_at.strftime("%d %b %H:%M") for v in vitals],
        "temperature": [float(v.temperature_c) if v.temperature_c is not None else None for v in vitals],
        "pulse": [v.pulse_rate for v in vitals],
        "systolic": [v.blood_pressure_systolic for v in vitals],
        "diastolic": [v.blood_pressure_diastolic for v in vitals],
    }
    recent_labs = []
    for lab in patient.lab_orders.select_related("test").order_by("-created_at")[:5]:
        try:
            result = lab.result
        except ObjectDoesNotExist:
            result = None
        recent_labs.append(
            {
                "name": lab.test.name,
                "status": lab.get_status_display(),
                "value": result.display_value if result else "Awaiting result",
                "is_abnormal": getattr(result, "is_abnormal", False),
                "is_critical": getattr(result, "is_critical", False),
            }
        )
    recent_imaging = patient.imaging_requests.select_related("modality").order_by("-created_at")[:5]
    recent_alerts = patient.alerts.select_related("acknowledged_by").order_by("-raised_at")[:5]
    latest_vitals = patient.vital_sign_sets.select_related("ews").first()
    latest_vitals_summary = None
    if latest_vitals:
        latest_vitals_summary = {
            "temperature_c": latest_vitals.temperature_c,
            "bp": f"{latest_vitals.blood_pressure_systolic or '-'} / {latest_vitals.blood_pressure_diastolic or '-'}",
            "pulse": latest_vitals.pulse_rate,
            "ews_score": getattr(getattr(latest_vitals, "ews", None), "score", None),
        }
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
        {"id": "referrals", "label": "Referrals", "badge": patient.referrals.count()},
    ]
    return render(
        request,
        "patients/profile.html",
        {
            "patient": patient,
            "tabs": tabs,
            "vitals_chart": vitals_chart,
            "recent_labs": recent_labs,
            "recent_imaging": recent_imaging,
            "recent_alerts": recent_alerts,
            "latest_vitals": latest_vitals_summary,
            "open_alerts": patient.alerts.filter(acknowledged_by__isnull=True).count(),
            "critical_alerts": patient.alerts.filter(severity="critical").count(),
        },
    )
