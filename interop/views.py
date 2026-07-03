from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from patients.models import Patient

from .serializers import FHIRBundleSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def patient_bundle(request, patient_id):
    """Return a FHIR-Bundle-shaped document for the given patient.
    Read-only; no conformance claim beyond 'FHIR-inspired export'.
    """
    patient = get_object_or_404(Patient.objects.prefetch_related("encounters"), pk=patient_id)
    encounters = patient.encounters.all().order_by("-created_at")[:10]
    serializer = FHIRBundleSerializer({"patient": patient, "encounters": list(encounters)})
    return Response(serializer.data)
