from django.urls import path

from . import views

app_name = "imaging"

urlpatterns = [
    path("patient/<int:patient_id>/request/", views.request_imaging, name="request"),
    path("patient/<int:patient_id>/tab/", views.patient_tab, name="patient_tab"),
    path("request/<int:pk>/report/", views.enter_report, name="report"),
    path("report/<int:pk>/", views.report_detail, name="report_detail"),
    path("worklist/", views.worklist, name="worklist"),
]

