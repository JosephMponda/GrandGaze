from django import forms

from .models import DispensingRecord, Prescription


class PrescriptionForm(forms.ModelForm):
    proceed_with_warnings = forms.BooleanField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Prescription
        fields = ["encounter", "drug", "dose", "route", "frequency", "duration_days", "safety_override_reason"]


class DispensingRecordForm(forms.ModelForm):
    class Meta:
        model = DispensingRecord
        fields = ["quantity_dispensed", "stock_note"]

