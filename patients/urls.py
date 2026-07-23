from django.urls import path

from . import views

app_name = "patients"

urlpatterns = [
    path("", views.patient_list, name="list"),
    path("register/", views.register_patient, name="register"),
    path("search/", views.search_patients, name="search"),
    path("<int:pk>/edit/", views.edit_patient, name="edit"),
    path("<int:pk>/", views.patient_profile, name="profile"),
]
