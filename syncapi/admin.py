from django.contrib import admin

from .models import SyncConflict, SyncSubmission


@admin.register(SyncSubmission)
class SyncSubmissionAdmin(admin.ModelAdmin):
    list_display = ("client_uuid", "form_type", "status", "received_at", "applied_at")
    list_filter = ("form_type", "status")
    search_fields = ("client_uuid",)


@admin.register(SyncConflict)
class SyncConflictAdmin(admin.ModelAdmin):
    list_display = ("submission", "resolved_at")
