from django.urls import path

from . import views

app_name = "reporting"

urlpatterns = [
    path("alerts/recent/", views.recent_alerts, name="recent_alerts"),
]
