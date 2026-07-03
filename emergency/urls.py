from django.urls import path
from . import views

app_name = "emergency"

urlpatterns = [
    path("triage/<int:patient_id>/", views.triage_patient, name="triage"),
    path("rapid-register/", views.rapid_register, name="rapid_register"),
    path("queue/", views.queue, name="queue"),
    path("resolve/<int:pk>/", views.resolve, name="resolve"),
    path("patient/<int:patient_id>/tab/", views.patient_tab, name="patient_tab"),
]
