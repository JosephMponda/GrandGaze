from django.urls import path

from . import views

app_name = "encounters"

urlpatterns = [
    path("patient/<int:patient_id>/new/", views.new_encounter, name="new"),
    path("patient/<int:patient_id>/tab/", views.patient_encounters_tab, name="patient_tab"),
    path("patient/<int:patient_id>/allergies/add/", views.add_allergy, name="add_allergy"),
    path("<int:pk>/", views.encounter_detail, name="detail"),
    path("<int:pk>/edit/", views.edit_encounter, name="edit"),
]
