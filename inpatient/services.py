from django.db.models import QuerySet
from django.utils import timezone

from .models import Admission, AdmissionStatus, Bed, Ward, WardRoundNote


def admit_patient(patient, clinician, diagnosis, encounter=None, bed=None) -> Admission:
    admission = Admission.objects.create(
        patient=patient, admitting_clinician=clinician,
        admission_diagnosis=diagnosis, encounter=encounter,
    )
    if bed:
        assign_bed(admission, bed)
    return admission


def assign_bed(admission: Admission, bed: Bed) -> Bed:
    bed.is_occupied = True
    bed.save(update_fields=["is_occupied"])
    admission.bed = bed
    admission.save(update_fields=["bed"])
    return bed


def free_bed(bed: Bed):
    bed.is_occupied = False
    bed.save(update_fields=["is_occupied"])


def transfer_patient(admission: Admission, target_bed: Bed, reason: str = "") -> Admission:
    old_bed = admission.bed
    if old_bed:
        free_bed(old_bed)
    assign_bed(admission, target_bed)
    return admission


def discharge(admission: Admission, clinician, summary="", disposition="discharged") -> Admission:
    if admission.bed:
        free_bed(admission.bed)
    admission.status = AdmissionStatus.DEAD if disposition == "dead" else AdmissionStatus.DISCHARGED
    admission.discharged_at = timezone.now()
    admission.discharge_summary = summary
    admission.discharge_disposition = disposition
    admission.save(update_fields=["status", "discharged_at", "discharge_summary", "discharge_disposition"])
    return admission


def ward_occupancy(ward: Ward) -> dict:
    total = ward.beds.count()
    occupied = ward.beds.filter(is_occupied=True).count()
    return {"total_beds": total, "occupied_beds": occupied, "free_beds": total - occupied}


def active_admissions() -> QuerySet[Admission]:
    return Admission.objects.filter(status=AdmissionStatus.ACTIVE).select_related("patient", "bed__ward")


def add_ward_round_note(admission, clinician, note, diagnosis_update="", plan_update="") -> WardRoundNote:
    return WardRoundNote.objects.create(
        admission=admission, clinician=clinician,
        note=note, diagnosis_update=diagnosis_update, plan_update=plan_update,
    )


def available_beds(ward=None) -> QuerySet[Bed]:
    beds = Bed.objects.filter(is_occupied=False).select_related("ward")
    if ward:
        beds = beds.filter(ward=ward)
    return beds
