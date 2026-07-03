from django.contrib import admin

from .models import LabOrder, LabResult, LabTest


admin.site.register(LabTest)
admin.site.register(LabOrder)
admin.site.register(LabResult)

