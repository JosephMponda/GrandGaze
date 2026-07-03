from django.urls import path

from . import views

app_name = "laboratory"

urlpatterns = [
    path("patient/<int:patient_id>/order/", views.order_test, name="order"),
    path("patient/<int:patient_id>/tab/", views.patient_tab, name="patient_tab"),
    path("order/<int:pk>/collect/", views.collect_specimen, name="collect"),
    path("order/<int:pk>/result/", views.enter_result, name="enter_result"),
    path("result/<int:pk>/", views.result_detail, name="result_detail"),
    path("result/<int:pk>/verify/", views.verify_result, name="verify_result"),
    path("workload/", views.workload, name="workload"),
]

