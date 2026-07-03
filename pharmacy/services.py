from django.db.models import QuerySet
from django.utils import timezone

from .models import DispensingRecord, Drug, Prescription, PrescriptionStatus, StockLevel
from .safety import CriticalSafetyBlock, check_prescription_safety


def prescribe(patient, drug, prescribed_by, data) -> tuple[Prescription, list]:
    warnings = check_prescription_safety(patient, drug, data.get("dose"))
    critical = [w for w in warnings if w.level == "critical"]
    if critical:
        raise CriticalSafetyBlock(
            "A critical medication safety warning blocks this prescription and cannot be overridden here.",
            warnings,
        )
    if warnings and not data.get("safety_override_reason"):
        raise ValueError("A safety override reason is required when medication warnings are present.")
    prescription = Prescription.objects.create(patient=patient, drug=drug, prescribed_by=prescribed_by, **data)
    return prescription, warnings


def approve(prescription: Prescription, approved_by) -> Prescription:
    prescription.status = PrescriptionStatus.APPROVED
    prescription.approved_by = approved_by
    prescription.approved_at = timezone.now()
    prescription.save(update_fields=["status", "approved_by", "approved_at"])
    return prescription


def dispense(prescription: Prescription, dispensed_by, data) -> DispensingRecord:
    return DispensingRecord.objects.create(prescription=prescription, dispensed_by=dispensed_by, **data)


def active_prescriptions_for(patient) -> QuerySet[Prescription]:
    return Prescription.objects.filter(
        patient=patient,
        status__in=[PrescriptionStatus.PRESCRIBED, PrescriptionStatus.APPROVED, PrescriptionStatus.DISPENSED],
    )


def check_stock(drug: Drug) -> tuple[int, bool]:
    level = StockLevel.objects.filter(drug=drug).first()
    qty = level.quantity if level else 0
    return qty, qty > 0


def adjust_stock(drug: Drug, quantity: int, adjusted_by, note: str = "") -> StockLevel:
    level, _ = StockLevel.objects.get_or_create(drug=drug, defaults={"quantity": 0})
    level.quantity += quantity
    level.save(update_fields=["quantity"])
    return level
