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


# ── Offline sync forms ──────────────────────────────────────────────────


class OfflineLabOrderForm(forms.Form):
    patient_id = forms.IntegerField()
    test_id = forms.IntegerField()
    encounter_id = forms.IntegerField(required=False)


class OfflineLabResultForm(forms.Form):
    order_id = forms.IntegerField()
    value_numeric = forms.DecimalField(required=False, max_digits=10, decimal_places=2)
    value_text = forms.CharField(required=False, max_length=100)
    notes = forms.CharField(required=False)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("value_numeric") is None and not cleaned.get("value_text"):
            raise forms.ValidationError("Enter either a numeric or text result.")
        return cleaned


class OfflineLabVerifyForm(forms.Form):
    result_id = forms.IntegerField()


class OfflineLabCollectForm(forms.Form):
    order_id = forms.IntegerField()

