"""FHIR-inspired serializers — read-only export, not a certified FHIR server."""

from rest_framework import serializers


class FHIRPatientSerializer(serializers.Serializer):
    resourceType = serializers.CharField(default="Patient", read_only=True)
    id = serializers.SerializerMethodField()
    identifier = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    gender = serializers.CharField(source="sex")
    birthDate = serializers.DateField(source="date_of_birth", allow_null=True)

    def get_id(self, obj):
        return f"Patient/{obj.pk}"

    def get_identifier(self, obj):
        return [
            {"system": "https://must.ac.mw/emr/patient-number", "value": obj.patient_number},
        ]

    def get_name(self, obj):
        parts = [obj.first_name, obj.last_name]
        if obj.other_names:
            parts.append(obj.other_names)
        return [{"text": " ".join(parts), "family": obj.last_name, "given": [obj.first_name]}]


class FHIREncounterSerializer(serializers.Serializer):
    resourceType = serializers.CharField(default="Encounter", read_only=True)
    id = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    period = serializers.SerializerMethodField()
    reasonCode = serializers.SerializerMethodField()

    def get_id(self, obj):
        return f"Encounter/{obj.pk}"

    def get_status(self, obj):
        return "finished" if obj.signed_at else "in-progress"

    def get_period(self, obj):
        return {"start": obj.created_at.isoformat() if obj.created_at else None}

    def get_reasonCode(self, obj):
        codes = []
        if obj.presenting_complaint:
            codes.append({"text": obj.presenting_complaint})
        if obj.icd_code:
            codes.append({"coding": [{"system": "http://hl7.org/fhir/sid/icd-11", "code": obj.icd_code, "display": obj.icd_display or obj.icd_code}]})
        return codes


class FHIRBundleSerializer(serializers.Serializer):
    resourceType = serializers.CharField(default="Bundle", read_only=True)
    type = serializers.CharField(default="collection", read_only=True)
    entry = serializers.SerializerMethodField()

    def get_entry(self, obj):
        patient = obj["patient"]
        encounters = obj.get("encounters", [])
        entries = [
            {
                "resource": FHIRPatientSerializer(patient).data,
                "fullUrl": f"https://must.ac.mw/emr/Patient/{patient.pk}",
            }
        ]
        for enc in encounters:
            entries.append({
                "resource": FHIREncounterSerializer(enc).data,
                "fullUrl": f"https://must.ac.mw/emr/Encounter/{enc.pk}",
            })
        return entries
