from django import forms

from .models import ImagingReport, ImagingRequest


class ImagingRequestForm(forms.ModelForm):
    class Meta:
        model = ImagingRequest
        fields = ["encounter", "modality", "clinical_indication", "pregnancy_status_checked", "scheduled_at"]
        widgets = {"scheduled_at": forms.DateTimeInput(attrs={"type": "datetime-local"})}

    def clean(self):
        cleaned = super().clean()
        modality = cleaned.get("modality")
        if modality and modality.requires_pregnancy_check and not cleaned.get("pregnancy_status_checked"):
            self.add_error("pregnancy_status_checked", "Confirm pregnancy-status safety check before requesting this modality.")
        return cleaned


class ImagingReportForm(forms.ModelForm):
    class Meta:
        model = ImagingReport
        fields = ["findings", "impression", "is_critical_finding", "image_reference"]

