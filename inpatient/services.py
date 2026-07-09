from django.db.models import QuerySet
from django.utils import timezone

from .models import (
    Admission, AdmissionStatus, Bed, FluidBalanceEntry, MedicationAdministrationRecord,
    NursingAssessment, NursingCarePlan, ProcedureNote, Ward, WardRoundNote,
)


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


def discharge(admission: Admission, clinician, summary="", disposition="discharged", cause_of_death="", death_certificate_issued=False) -> Admission:
    if admission.bed:
        free_bed(admission.bed)
    admission.status = AdmissionStatus.DEAD if disposition == "dead" else AdmissionStatus.DISCHARGED
    admission.discharged_at = timezone.now()
    admission.discharge_summary = summary
    admission.discharge_disposition = disposition
    admission.cause_of_death = cause_of_death
    admission.death_certificate_issued = death_certificate_issued
    admission.save(update_fields=["status", "discharged_at", "discharge_summary", "discharge_disposition", "cause_of_death", "death_certificate_issued"])
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


# ── MAR ──────────────────────────────────────────────────────────────────


def record_administration(admission, prescription, user, dose, route, site="", notes="") -> MedicationAdministrationRecord:
    return MedicationAdministrationRecord.objects.create(
        admission=admission, prescription=prescription, administered_by=user,
        dose_given=dose, route=route, site=site, notes=notes,
    )


def mar_for_admission(admission) -> QuerySet[MedicationAdministrationRecord]:
    return MedicationAdministrationRecord.objects.filter(admission=admission).select_related(
        "prescription__drug", "administered_by",
    )


# ── Nursing Care Plans ───────────────────────────────────────────────────


def create_care_plan(admission, user, problem, goal, interventions) -> NursingCarePlan:
    return NursingCarePlan.objects.create(
        admission=admission, problem=problem, goal=goal,
        interventions=interventions, created_by=user,
    )


def evaluate_care_plan(care_plan, user, evaluation, status) -> NursingCarePlan:
    care_plan.evaluated_by = user
    care_plan.evaluation = evaluation
    care_plan.goal_status = status
    care_plan.save(update_fields=["evaluated_by", "evaluation", "goal_status"])
    return care_plan


def active_care_plans(admission) -> QuerySet[NursingCarePlan]:
    return NursingCarePlan.objects.filter(
        admission=admission, goal_status=NursingCarePlan.GoalStatus.ONGOING,
    )


# ── Fluid Balance ────────────────────────────────────────────────────────


def record_fluid(admission, user, fluid_type, volume_ml) -> FluidBalanceEntry:
    return FluidBalanceEntry.objects.create(
        admission=admission, fluid_type=fluid_type,
        volume_ml=volume_ml, recorded_by=user,
    )


def fluid_balance_summary(admission) -> dict:
    entries = FluidBalanceEntry.objects.filter(admission=admission)
    intake = sum(e.volume_ml for e in entries if e.is_intake)
    output = sum(e.volume_ml for e in entries if not e.is_intake)
    return {"intake_ml": intake, "output_ml": output, "net_ml": intake - output, "entries": entries}


# ── Procedure Notes ──────────────────────────────────────────────────────


def create_procedure_note(admission, user, **data) -> ProcedureNote:
    assistants = data.pop("assistants", [])
    note = ProcedureNote.objects.create(admission=admission, performed_by=user, **data)
    if assistants:
        note.assistants.set(assistants)
    return note


def procedure_notes_for_admission(admission) -> QuerySet[ProcedureNote]:
    return ProcedureNote.objects.filter(admission=admission).select_related("performed_by")


# ── Nursing Assessment ───────────────────────────────────────────────────


def create_nursing_assessment(admission, user, assessment_note, problems=None) -> NursingAssessment:
    return NursingAssessment.objects.create(
        admission=admission, assessment_note=assessment_note,
        problems=problems or [], assessed_by=user,
    )
