from django.contrib import admin

from .models import EarlyWarningScore, VitalSignSet


class EarlyWarningScoreInline(admin.StackedInline):
    model = EarlyWarningScore
    extra = 0


@admin.register(VitalSignSet)
class VitalSignSetAdmin(admin.ModelAdmin):
    list_display = ("patient", "recorded_at", "temperature_c", "blood_pressure_systolic", "oxygen_saturation", "recorded_by")
    search_fields = ("patient__patient_number",)
    inlines = [EarlyWarningScoreInline]
