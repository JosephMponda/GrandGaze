from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("patients/", include("patients.urls")),
    path("encounters/", include("encounters.urls")),
    path("vitals/", include("vitals.urls")),
    path("reporting/", include("reporting.urls")),
    path("", RedirectView.as_view(pattern_name="accounts:dashboard", permanent=False)),
]
