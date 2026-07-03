from django.contrib import admin

from .models import AlertEvent


@admin.register(AlertEvent)
class AlertEventAdmin(admin.ModelAdmin):
    list_display = ("patient", "source", "severity", "raised_at", "acknowledged_by")
    list_filter = ("source", "severity")
