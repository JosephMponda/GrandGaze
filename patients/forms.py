from django import forms

from .models import NextOfKin, Patient


class PatientRegistrationForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            "national_id",
            "first_name",
            "last_name",
            "other_names",
            "sex",
            "date_of_birth",
            "age_estimated",
            "phone_number",
            "address_line",
            "village",
            "traditional_authority",
            "district",
            "region",
            "occupation_or_school",
            "patient_category",
            "consent_care",
            "consent_teaching",
            "consent_research",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
        }

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("date_of_birth") and not cleaned.get("age_estimated"):
            self.add_error(
                "age_estimated",
                "If date of birth is unknown, confirm age is estimated (Malawi context: DOB often unavailable).",
            )
        return cleaned


class NextOfKinForm(forms.ModelForm):
    class Meta:
        model = NextOfKin
        fields = ["name", "relationship", "phone_number"]
