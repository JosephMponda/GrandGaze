from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import render
from django.urls import include, path
from django.views.generic import RedirectView, TemplateView

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from config.error_views import bad_request, page_not_found, permission_denied, server_error
from config.health_check import health_check


def catch_all_404(request, unmatched=""):
    return render(request, "404.html", status=404)

handler400 = "config.error_views.bad_request"
handler404 = "config.error_views.page_not_found"
handler403 = "config.error_views.permission_denied"
handler500 = "config.error_views.server_error"

urlpatterns = [
    path("django-admin/", admin.site.urls),
    
    # Root URL - Redirect to landing page
    path("", RedirectView.as_view(pattern_name="accounts:landing", permanent=False)),
    
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
    path("emergency/", include("emergency.urls")),
    path("dialysis/", include("dialysis.urls")),
    path("inpatient/", include("inpatient.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("health/", health_check, name="health_check"),
    path("<path:unmatched>", catch_all_404, name="catch_all"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)