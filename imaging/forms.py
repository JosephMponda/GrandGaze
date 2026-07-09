from django import forms

from .models import ImagingReport, ImagingRequest


class ImagingRequestForm(forms.ModelForm):
    class Meta:
        model = ImagingRequest  # Or whatever their imaging model is named
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
        
class ImagingReportForm(forms.ModelForm):
    class Meta:
        model = ImagingReport
        fields = ["findings", "impression", "is_critical_finding", "image_reference"]

