from django.urls import path

from . import views

app_name = "interop"

urlpatterns = [
    path("interop/patient/<int:patient_id>/bundle/", views.patient_bundle, name="patient_bundle"),
]
