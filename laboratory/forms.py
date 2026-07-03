from django import forms

from .models import LabOrder, LabResult


class LabOrderForm(forms.ModelForm):
    class Meta:
        model = LabOrder
        fields = ["test", "encounter"]


class LabResultForm(forms.ModelForm):
    class Meta:
        model = LabResult
        fields = ["value_numeric", "value_text", "notes"]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("value_numeric") is None and not cleaned.get("value_text"):
            raise forms.ValidationError("Enter either a numeric or text result.")
        return cleaned

