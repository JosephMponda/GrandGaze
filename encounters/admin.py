from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import AllergyRecord, ClinicalTemplate, Encounter, EncounterAddendum


class EncounterAddendumInline(admin.TabularInline):
    model = EncounterAddendum
    extra = 0


@admin.register(Encounter)
class EncounterAdmin(SimpleHistoryAdmin):
    list_display = ("patient", "clinician", "encounter_type", "status", "is_signed", "created_at")
    list_filter = ("encounter_type", "status")
    search_fields = ("patient__patient_number", "patient__first_name", "patient__last_name")
    inlines = [EncounterAddendumInline]


@admin.register(AllergyRecord)
class AllergyRecordAdmin(admin.ModelAdmin):
    list_display = ("patient", "allergen", "severity", "recorded_by", "recorded_at")
    list_filter = ("severity",)


@admin.register(ClinicalTemplate)
class ClinicalTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "specialty")
