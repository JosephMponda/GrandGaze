from django.urls import path

from . import views

app_name = "billing"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("patient/<int:patient_id>/", views.patient_invoices, name="patient_invoices"),
    path("patient/<int:patient_id>/tab/", views.patient_tab, name="patient_tab"),
    path("patient/<int:patient_id>/create/", views.create_invoice_view, name="create_invoice"),
    path("invoice/<int:invoice_id>/", views.invoice_detail, name="invoice_detail"),
    path("invoice/<int:invoice_id>/print/", views.invoice_print, name="invoice_print"),
]
