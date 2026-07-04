from django.urls import path

from . import views

app_name = "pharmacy"

urlpatterns = [
    path("patient/<int:patient_id>/prescribe/", views.prescribe, name="prescribe"),
    path("patient/<int:patient_id>/tab/", views.patient_tab, name="patient_tab"),
    path("queue/", views.queue, name="queue"),
    path("prescription/<int:pk>/cancel/", views.cancel, name="cancel"),
    path("prescription/<int:pk>/approve/", views.approve, name="approve"),
    path("prescription/<int:pk>/dispense/", views.dispense, name="dispense"),
    path("stock/", views.stock_adjust, name="stock"),
]

