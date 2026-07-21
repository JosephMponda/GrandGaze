from django import forms

from .models import (
    FluidBalanceEntry,
    MedicationAdministrationRecord,
    NursingAssessment,
    NursingCarePlan,
    ProcedureNote,
    WardRoundNote,
)


class WardRoundNoteForm(forms.Form):
    note = forms.CharField(widget=forms.Textarea)
    diagnosis_update = forms.CharField(required=False)
    plan_update = forms.CharField(required=False)


class MAREntryForm(forms.Form):
    prescription = forms.IntegerField()
    dose_given = forms.CharField(max_length=80)
    route = forms.ChoiceField(choices=MedicationAdministrationRecord.AdministrationRoute.choices)
    site = forms.CharField(required=False, max_length=80)
    notes = forms.CharField(required=False)


class CarePlanForm(forms.Form):
    problem = forms.CharField(max_length=300)
    goal = forms.CharField()
    interventions = forms.CharField()


class CarePlanEvaluateForm(forms.Form):
    care_plan_id = forms.IntegerField()
    evaluation = forms.CharField()
    goal_status = forms.ChoiceField(choices=NursingCarePlan.GoalStatus.choices)


class FluidBalanceEntryForm(forms.Form):
    fluid_type = forms.ChoiceField(choices=FluidBalanceEntry.FluidType.choices)
    volume_ml = forms.IntegerField(min_value=1)


class ProcedureNoteForm(forms.Form):
    procedure_name = forms.CharField(max_length=200)
    indication = forms.CharField(required=False)
    anaesthesia_type = forms.CharField(required=False, max_length=50)
    findings = forms.CharField()
    complications = forms.CharField(required=False)
    outcome = forms.CharField(required=False, max_length=200)
    notes = forms.CharField(required=False)


class NursingAssessmentForm(forms.Form):
    assessment_note = forms.CharField()
    problems = forms.JSONField(required=False)


class ReferralForm(forms.Form):
    destination = forms.CharField(max_length=200)
    reason = forms.CharField(required=False)
    source = forms.CharField(required=False, max_length=200)
