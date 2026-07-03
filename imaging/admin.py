from django.contrib import admin

from .models import ImagingModality, ImagingReport, ImagingRequest


admin.site.register(ImagingModality)
admin.site.register(ImagingRequest)
admin.site.register(ImagingReport)

