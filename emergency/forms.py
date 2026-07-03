from django import forms
from django.contrib.auth.models import User
from django.utils import timezone

from patients.models import Patient

from .models import TriageCategory, TriageEncounter


class TriageForm(forms.Form):
    triage_category = forms.ChoiceField(choices=TriageCategory.choices, label="Triage Category")
    presenting_condition = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), label="Presenting Condition / Complaint")
    outcome = forms.ChoiceField(choices=[("", "———")] + list(TriageEncounter._meta.get_field("outcome").flatchoices), required=False, label="Outcome (optional)")
    disposition_note = forms.CharField(widget=forms.Textarea(attrs={"rows": 2, "placeholder": "e.g. referred to surgical team"}), required=False, label="Disposition Note (optional)")

    def save(self, patient, triaged_by) -> TriageEncounter:
        encounter = TriageEncounter.objects.create(
            patient=patient,
            triaged_by=triaged_by,
            triage_category=self.cleaned_data["triage_category"],
            presenting_condition=self.cleaned_data["presenting_condition"],
            outcome=self.cleaned_data.get("outcome") or None,
            disposition_note=self.cleaned_data.get("disposition_note", ""),
            resolved_at=timezone.now() if self.cleaned_data.get("outcome") else None,
        )
        return encounter


class RapidRegisterForm(forms.Form):
    first_name = forms.CharField(max_length=150, label="First Name")
    last_name = forms.CharField(max_length=150, label="Last Name")
    sex = forms.ChoiceField(choices=Patient._meta.get_field("sex").flatchoices, label="Sex")
    age_estimated = forms.BooleanField(required=False, label="Age is estimated")
    triage_category = forms.ChoiceField(choices=TriageCategory.choices, label="Triage Category")
    presenting_condition = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), label="Presenting Condition / Complaint")

    def save(self, registered_by) -> tuple[Patient, TriageEncounter]:
        patient = Patient.objects.create(
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
            sex=self.cleaned_data["sex"],
            age_estimated=self.cleaned_data.get("age_estimated", False),
            registered_by=registered_by,
        )
        encounter = TriageEncounter.objects.create(
            patient=patient,
            triaged_by=registered_by,
            triage_category=self.cleaned_data["triage_category"],
            presenting_condition=self.cleaned_data["presenting_condition"],
            rapid_registration=True,
        )
        return patient, encounter
