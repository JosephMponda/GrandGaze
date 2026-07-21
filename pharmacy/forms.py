from django import forms

from .models import DispensingRecord, Drug, Prescription


class PrescriptionForm(forms.ModelForm):
    proceed_with_warnings = forms.BooleanField(required=False, widget=forms.CheckboxInput)

    class Meta:
        model = Prescription
        fields = ["encounter", "drug", "dose", "route", "frequency", "duration_days", "safety_override_reason", "notes"]
        widgets = {
            "safety_override_reason": forms.Textarea(attrs={"rows": 3, "class": "form-textarea"}),
            "notes": forms.Textarea(attrs={"rows": 3, "class": "form-textarea"}),
        }


class DispensingRecordForm(forms.ModelForm):
    class Meta:
        model = DispensingRecord
        fields = ["quantity_dispensed", "stock_note"]


class StockAdjustForm(forms.Form):
    drug = forms.ModelChoiceField(queryset=Drug.objects.all(), label="Drug")
    quantity = forms.IntegerField(min_value=1, label="Quantity to add")
    note = forms.CharField(widget=forms.TextInput(attrs={"placeholder": "e.g. delivery from Central Medical Stores"}), required=False, label="Note")


# ── Offline sync forms ──────────────────────────────────────────────────


class OfflinePrescribeForm(forms.Form):
    patient_id = forms.IntegerField()
    drug_id = forms.IntegerField()
    encounter_id = forms.IntegerField(required=False)
    dose = forms.CharField(max_length=80)
    route = forms.CharField(max_length=40)
    frequency = forms.CharField(max_length=80)
    duration_days = forms.IntegerField(required=False)
    safety_override_reason = forms.CharField(required=False)
    notes = forms.CharField(required=False)


class OfflineApproveForm(forms.Form):
    prescription_id = forms.IntegerField()


class OfflineDispenseForm(forms.Form):
    prescription_id = forms.IntegerField()
    quantity_dispensed = forms.CharField(max_length=80)
    stock_note = forms.CharField(required=False, max_length=200)