from django.urls import path

from . import views

app_name = "billing"

urlpatterns = [
    path("patient/<int:patient_id>/", views.patient_invoices, name="patient_invoices"),
    path("patient/<int:patient_id>/create/", views.create_invoice_view, name="create_invoice"),
    path("invoice/<int:invoice_id>/", views.invoice_detail, name="invoice_detail"),
]
