from django import forms

from .models import DialysisPrescription, VascularAccess


class DialysisPrescriptionForm(forms.ModelForm):
    class Meta:
        model = DialysisPrescription
        fields = ["frequency_per_week", "target_fluid_removal_l", "vascular_access"]
        widgets = {
            "frequency_per_week": forms.NumberInput(attrs={"min": 1, "max": 7}),
            "target_fluid_removal_l": forms.NumberInput(attrs={"step": "0.1", "min": "0"}),
        }


# ── Offline sync forms ──────────────────────────────────────────────────


class OfflineDialysisPrescriptionForm(forms.Form):
    patient_id = forms.IntegerField()
    frequency_per_week = forms.IntegerField(min_value=1, max_value=7)
    target_fluid_removal_l = forms.DecimalField(required=False, max_digits=4, decimal_places=2)
    vascular_access = forms.ChoiceField(choices=VascularAccess.choices)


class OfflineDialysisSessionForm(forms.Form):
    prescription_id = forms.IntegerField()
    pre_weight_kg = forms.DecimalField(max_digits=5, decimal_places=1)
    post_weight_kg = forms.DecimalField(max_digits=5, decimal_places=1)
    complications = forms.CharField(required=False, max_length=500)
    notes = forms.CharField(required=False, max_length=500)
