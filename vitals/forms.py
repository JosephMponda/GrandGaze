from django import forms

from .models import VitalSignSet


class VitalSignSetForm(forms.ModelForm):
    class Meta:
        model = VitalSignSet
        fields = [
            "temperature_c",
            "blood_pressure_systolic",
            "blood_pressure_diastolic",
            "pulse_rate",
            "respiratory_rate",
            "oxygen_saturation",
            "weight_kg",
            "height_cm",
            "pain_score",
            "blood_glucose",
            "glasgow_coma_scale",
            "pregnancy_status",
        ]
