from django.urls import path

from . import views

app_name = "syncapi"

urlpatterns = [
    path("sync/submit/", views.sync_submit, name="sync_submit"),
    path("sync/status/", views.sync_status, name="sync_status"),
    path("offline/bootstrap/", views.offline_bootstrap, name="offline_bootstrap"),
]
