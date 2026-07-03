from django.urls import path

from . import views

app_name = "reporting"

urlpatterns = [
    path("alerts/recent/", views.recent_alerts, name="recent_alerts"),
    path("alerts/<int:alert_id>/acknowledge/", views.acknowledge_alert, name="acknowledge_alert"),
    path("analytics/", views.analytics_dashboard, name="analytics_dashboard"),
]
