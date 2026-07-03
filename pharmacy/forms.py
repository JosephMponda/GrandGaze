from django import forms

from .models import DispensingRecord, Drug, Prescription


class PrescriptionForm(forms.ModelForm):
    proceed_with_warnings = forms.BooleanField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Prescription
        fields = ["encounter", "drug", "dose", "route", "frequency", "duration_days", "safety_override_reason"]


class DispensingRecordForm(forms.ModelForm):
    class Meta:
        model = DispensingRecord
        fields = ["quantity_dispensed", "stock_note"]


class StockAdjustForm(forms.Form):
    drug = forms.ModelChoiceField(queryset=Drug.objects.all(), label="Drug")
    quantity = forms.IntegerField(min_value=1, label="Quantity to add")
    note = forms.CharField(widget=forms.TextInput(attrs={"placeholder": "e.g. delivery from Central Medical Stores"}), required=False, label="Note")

