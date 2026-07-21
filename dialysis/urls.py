from django.urls import path

from . import views

app_name = "dialysis"

urlpatterns = [
    path("patient/<int:patient_id>/tab/", views.patient_tab, name="patient_tab"),
    path("patient/<int:patient_id>/prescribe/", views.create_prescription, name="create_prescription"),
    path("session/<int:prescription_id>/record/", views.record_session, name="record_session"),
    path("dashboard/", views.dashboard, name="dashboard"),
]