from django import forms

from .models import ImagingReport, ImagingRequest


class ImagingRequestForm(forms.ModelForm):
    class Meta:
        model = ImagingRequest
        fields = [
            "modality",
            "clinical_indication",
            "encounter",
            "pregnancy_status_checked",
            "scheduled_at",
        ]
        widgets = {
            "clinical_indication": forms.Textarea(attrs={"rows": 3, "class": "form-textarea"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        modality = cleaned_data.get("modality")
        if modality and modality.requires_pregnancy_check and not cleaned_data.get("pregnancy_status_checked"):
            self.add_error(
                "pregnancy_status_checked",
                "This modality requires pregnancy status to be checked before ordering.",
            )
        return cleaned_data
class ImagingReportForm(forms.ModelForm):
    class Meta:
        model = ImagingReport
        fields = ["findings", "impression", "is_critical_finding", "image_reference"]

