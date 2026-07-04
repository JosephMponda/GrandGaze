from django.urls import path

from . import views

app_name = "inpatient"

urlpatterns = [
    path("admit/<int:patient_id>/", views.admit, name="admit"),
    path("admission/<int:pk>/", views.admission_detail, name="admission_detail"),
    path("ward/<int:ward_id>/", views.ward_dashboard, name="ward"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("patient/<int:patient_id>/tab/", views.patient_tab, name="patient_tab"),
    path("beds-for-ward/", views.beds_for_ward, name="beds_for_ward"),
]