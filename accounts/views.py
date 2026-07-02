from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from patients.models import Patient
from .dashboard_widgets import widgets_for_user
from .permissions import role_required


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
