from django.urls import path

from . import views

app_name = "vitals"

urlpatterns = [
    path("patient/<int:patient_id>/entry/", views.vitals_entry, name="entry"),
    path("patient/<int:patient_id>/tab/", views.patient_vitals_tab, name="patient_tab"),
]
