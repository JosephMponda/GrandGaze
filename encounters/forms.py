from django import forms

from .models import AllergyRecord, Encounter, EncounterAddendum


class EncounterForm(forms.ModelForm):
    class Meta:
        model = Encounter
        fields = [
            "encounter_type",
            "presenting_complaint",
            "history_of_presenting_complaint",
            "past_medical_history",
            "past_surgical_history",
            "medication_history",
            "allergy_history",
            "social_history",
            "family_history",
            "examination_findings",
            "diagnosis",
            "differential_diagnosis",
            "clinical_plan",
        ]


class EncounterAddendumForm(forms.ModelForm):
    class Meta:
        model = EncounterAddendum
        fields = ["note"]


class AllergyRecordForm(forms.ModelForm):
    class Meta:
        model = AllergyRecord
        fields = ["allergen", "reaction", "severity"]
