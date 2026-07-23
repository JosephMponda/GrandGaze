from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from django.core.exceptions import PermissionDenied

from accounts.permissions import has_role, role_required
from patients.services import get_patient_or_404

from . import services
from .forms import AllergyRecordForm, EncounterAddendumForm, EncounterForm
from .models import Encounter


@role_required("Clinician", "Nurse", "Admin")
def new_encounter(request, patient_id):
    patient = get_patient_or_404(patient_id)
    if request.method == "POST":
        form = EncounterForm(request.POST)
        if form.is_valid():
            encounter = services.create_encounter(patient, request.user, form.cleaned_data)
            messages.success(request, "Encounter created.")
            return redirect(reverse("encounters:detail", args=[encounter.pk]))
    else:
        form = EncounterForm()
    return render(request, "encounters/new.html", {"form": form, "patient": patient})


@login_required
def encounter_detail(request, pk):
    encounter = get_object_or_404(Encounter, pk=pk)

    if request.method == "POST" and "sign" in request.POST:
        if not has_role(request.user, "Clinician", "Nurse", "Admin"):
            raise PermissionDenied("Your role does not have access to this page.")
        if encounter.is_signed:
            messages.error(request, "This encounter is already signed.")
        else:
            services.sign_encounter(encounter, request.user)
            messages.success(request, "Encounter signed and locked.")
        return redirect(reverse("encounters:detail", args=[encounter.pk]))

    if request.method == "POST" and "add_addendum" in request.POST:
        if not has_role(request.user, "Clinician", "Nurse", "Admin"):
            raise PermissionDenied("Your role does not have access to this page.")
        # Signed encounters are read-only in the UI — further notes are
        # addenda, never a silent rewrite of signed clinical documentation.
        addendum_form = EncounterAddendumForm(request.POST)
        if addendum_form.is_valid():
            addendum = addendum_form.save(commit=False)
            addendum.encounter = encounter
            addendum.author = request.user
            addendum.save()
            messages.success(request, "Addendum added.")
        return redirect(reverse("encounters:detail", args=[encounter.pk]))

    addenda = encounter.addenda.all()
    edit_form = None if encounter.is_signed else EncounterForm(instance=encounter)
    return render(
        request,
        "encounters/detail.html",
        {
            "encounter": encounter,
            "patient": encounter.patient,
            "edit_form": edit_form,
            "addendum_form": EncounterAddendumForm(),
            "addenda": addenda,
        },
    )


@role_required("Clinician", "Nurse", "Admin")
def edit_encounter(request, pk):
    encounter = get_object_or_404(Encounter, pk=pk)
    if encounter.is_signed:
        messages.error(request, "Signed encounters are read-only - add an addendum instead.")
        return redirect(reverse("encounters:detail", args=[encounter.pk]))
    if request.method == "POST":
        form = EncounterForm(request.POST, instance=encounter)
        if form.is_valid():
            form.save()
            messages.success(request, "Encounter updated.")
            return redirect(reverse("encounters:detail", args=[encounter.pk]))
    return redirect(reverse("encounters:detail", args=[encounter.pk]))


@login_required
def open_encounters(request):
    encounters = Encounter.objects.filter(signed_at__isnull=True).select_related("patient", "clinician").order_by("-created_at")
    return render(request, "encounters/open_list.html", {"encounters": encounters})


@login_required
def patient_encounters_tab(request, patient_id):
    """HTMX partial plugged into Engineer A's patient profile template."""
    patient = get_patient_or_404(patient_id)
    encounters = patient.encounters.all()[:20]
    return render(request, "encounters/_patient_tab.html", {"patient": patient, "encounters": encounters})


@login_required
def add_allergy(request, patient_id):
    patient = get_patient_or_404(patient_id)
    if request.method == "POST":
        form = AllergyRecordForm(request.POST)
        if form.is_valid():
            allergy = form.save(commit=False)
            allergy.patient = patient
            allergy.recorded_by = request.user
            allergy.save()
            messages.success(request, "Allergy recorded.")
            return redirect(reverse("patients:profile", args=[patient.pk]))
    else:
        form = AllergyRecordForm()
    return render(request, "encounters/add_allergy.html", {"form": form, "patient": patient})
