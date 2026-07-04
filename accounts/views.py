from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse
from django.db import transaction

from patients.models import Patient
from inpatient.models import Ward, Bed
from .dashboard_widgets import widgets_for_user
from .permissions import role_required
from .forms import StaffUserForm

User = get_user_model()


@login_required
def dashboard(request):
    """Role-aware landing page - MVP requirement (brief §12)."""
    context = {
        "widgets": widgets_for_user(request.user),
    }
    return render(request, "accounts/dashboard.html", context)


@role_required("Admin", "ICT")
def audit_trail(request):
    """Read-only audit viewer over django-simple-history records.
    Satisfies brief §19.4 as a visible feature, not just a DB table.
    """
    patient_history = Patient.history.all().order_by("-history_date")[:200]
    return render(request, "accounts/audit_trail.html", {"patient_history": patient_history})


@role_required("Admin", "ICT")
def control_panel(request):
    """System configuration and user management dashboard."""
    users = User.objects.select_related("profile").all().order_by("username")
    wards = Ward.objects.all().order_by("name")
    return render(
        request,
        "accounts/control_panel.html",
        {"users": users, "wards": wards}
    )


@role_required("Admin", "ICT")
def add_user(request):
    """Create new EMR staff user and profile."""
    if request.method == "POST":
        form = StaffUserForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "New staff user account created.")
            return redirect(reverse("accounts:control_panel"))
    else:
        form = StaffUserForm()
    return render(request, "accounts/add_user.html", {"form": form})


@role_required("Admin", "ICT")
@transaction.atomic
def add_ward(request):
    """Create new ward and dynamically populate its beds."""
    if request.method == "POST":
        name = request.POST.get("name")
        department = request.POST.get("department", "")
        bed_count = request.POST.get("bed_count", "0")
        try:
            bed_count_int = int(bed_count)
            if not name or bed_count_int <= 0:
                messages.error(request, "Ward name and a valid bed count are required.")
            else:
                ward = Ward.objects.create(name=name, department=department, bed_count=bed_count_int)
                for i in range(1, bed_count_int + 1):
                    Bed.objects.create(ward=ward, label=f"Bed {i}")
                messages.success(request, f"Ward '{name}' created with {bed_count_int} beds.")
                return redirect(reverse("accounts:control_panel"))
        except ValueError:
            messages.error(request, "Invalid bed count value.")
    return render(request, "accounts/add_ward.html")
