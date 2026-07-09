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
            "icd_code",
            "icd_display",
            "differential_diagnosis",
            "clinical_plan",
        ]
        
        widgets = {
            "presenting_complaint": forms.Textarea(attrs={"rows": 3, "class": "form-textarea"}),
            "history_of_presenting_complaint": forms.Textarea(attrs={"rows": 3, "class": "form-textarea"}),
            "past_medical_history": forms.Textarea(attrs={"rows": 3, "class": "form-textarea"}),
            "past_surgical_history": forms.Textarea(attrs={"rows": 3, "class": "form-textarea"}),
            "medication_history": forms.Textarea(attrs={"rows": 3, "class": "form-textarea"}),
            "allergy_history": forms.Textarea(attrs={"rows": 3, "class": "form-textarea"}),
            "social_history": forms.Textarea(attrs={"rows": 3, "class": "form-textarea"}),
            "family_history": forms.Textarea(attrs={"rows": 3, "class": "form-textarea"}),
            "examination_findings": forms.Textarea(attrs={"rows": 3, "class": "form-textarea"}),
            "differential_diagnosis": forms.Textarea(attrs={"rows": 3, "class": "form-textarea"}),
            "clinical_plan": forms.Textarea(attrs={"rows": 3, "class": "form-textarea"}),
        }
        
class EncounterAddendumForm(forms.ModelForm):
    class Meta:
        model = EncounterAddendum
        fields = ["note"]
        widgets = {
            "note": forms.Textarea(attrs={"rows": 3, "class": "form-textarea"}),
        }


class AllergyRecordForm(forms.ModelForm):
    class Meta:
        model = AllergyRecord
        fields = ["allergen", "reaction", "severity"]
