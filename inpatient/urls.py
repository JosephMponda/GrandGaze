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
    # MAR (§8.1.4(g))
    path("admission/<int:admission_id>/mar/", views.mar_entry, name="mar_entry"),
    # Care Plans (§8.1.4(e))
    path("admission/<int:admission_id>/care-plans/", views.care_plan_list, name="care_plan_list"),
    path("admission/<int:admission_id>/care-plans/new/", views.care_plan_create, name="care_plan_create"),
    path("care-plan/<int:pk>/evaluate/", views.care_plan_evaluate, name="care_plan_evaluate"),
    # Fluid Balance (§8.1.4(f))
    path("admission/<int:admission_id>/fluid-balance/", views.fluid_balance, name="fluid_balance"),
    # Procedure Notes (§8.1.4(i))
    path("admission/<int:admission_id>/procedure-note/", views.procedure_note_create, name="procedure_note_create"),
    # Nursing Assessment (§8.1.6(a))
    path("admission/<int:admission_id>/nursing-assessments/", views.nursing_assessment_list, name="nursing_assessment_list"),
    path("admission/<int:admission_id>/nursing-assessments/new/", views.nursing_assessment_create, name="nursing_assessment_create"),
    # Referral (§8.1.2(g))
    path("referral/<int:patient_id>/", views.create_referral, name="create_referral"),
    path("referral/<int:patient_id>/tab/", views.referral_list, name="referral_tab"),
]