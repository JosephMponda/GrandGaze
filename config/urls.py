from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView, TemplateView

from config.health_check import health_check

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("patients/", include("patients.urls")),
    path("encounters/", include("encounters.urls")),
    path("vitals/", include("vitals.urls")),
    path("labs/", include("laboratory.urls")),
    path("imaging/", include("imaging.urls")),
    path("pharmacy/", include("pharmacy.urls")),
    path("reporting/", include("reporting.urls")),
    path("api/", include("syncapi.urls")),
    path("api/", include("interop.urls")),
    path("billing/", include("billing.urls")),
    path("health/", health_check, name="health_check"),
    path("", RedirectView.as_view(pattern_name="accounts:dashboard", permanent=False)),
]
