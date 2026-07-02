from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import NextOfKin, Patient, PatientMergeRecord, ReferralRecord


class NextOfKinInline(admin.TabularInline):
    model = NextOfKin
    extra = 0


@admin.register(Patient)
class PatientAdmin(SimpleHistoryAdmin):
    list_display = ("patient_number", "first_name", "last_name", "sex", "date_of_birth", "district", "patient_category", "is_active")
    list_filter = ("sex", "patient_category", "region", "is_active")
    search_fields = ("patient_number", "first_name", "last_name")
    inlines = [NextOfKinInline]
    readonly_fields = ("patient_number",)


@admin.register(PatientMergeRecord)
class PatientMergeRecordAdmin(admin.ModelAdmin):
    list_display = ("duplicate_patient", "primary_patient", "merged_by", "merged_at")


@admin.register(ReferralRecord)
class ReferralRecordAdmin(admin.ModelAdmin):
    list_display = ("patient", "source", "destination", "created_at")
