from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from .models import AlertEvent


@login_required
def recent_alerts(request):
    """Backs the 'patients with abnormal vitals in the last 4 hours'
    dashboard widget (Engineer B spec §4). Source-agnostic view over
    AlertEvent — other modules' alerts (lab, imaging) will show here too
    once Engineer E builds out the rest of `reporting`.
    """
    since = timezone.now() - timedelta(hours=4)
    alerts = AlertEvent.objects.filter(raised_at__gte=since).select_related("patient")
    return render(request, "reporting/recent_alerts.html", {"alerts": alerts})
