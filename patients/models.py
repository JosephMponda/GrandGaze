from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from core.encrypted_fields import EncryptedCharField, hash_lookup_value


class Sex(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"
    OTHER = "other", "Other"
    UNKNOWN = "unknown", "Unknown"


class Region(models.TextChoices):
    NORTHERN = "northern", "Northern"
    CENTRAL = "central", "Central"
    SOUTHERN = "southern", "Southern"


class PatientCategory(models.TextChoices):
    OUTPATIENT = "outpatient", "Outpatient"
    INPATIENT = "inpatient", "Inpatient"
    STUDENT = "student", "Student"
    STAFF = "staff", "Staff"
    PRIVATE = "private", "Private"
    REFERRED = "referred", "Referred"
    EMERGENCY = "emergency", "Emergency"
    RESEARCH = "research", "Research participant"


class Patient(models.Model):
    """Master Patient Index record. Brief §8.1.1.

    Every other app FKs into this model - never duplicate identity fields
    into another app's models (Engineer A spec §3).
    """

    patient_number = models.CharField(max_length=20, unique=True, editable=False)
    national_id = EncryptedCharField(max_length=64, blank=True)
    national_id_lookup = models.CharField(max_length=64, blank=True, db_index=True, editable=False)

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    other_names = models.CharField(max_length=150, blank=True)

    sex = models.CharField(max_length=10, choices=Sex.choices, default=Sex.UNKNOWN)
    date_of_birth = models.DateField(null=True, blank=True)
    age_estimated = models.BooleanField(default=False)  # Malawi context: DOB often unknown

    phone_number = EncryptedCharField(max_length=32, blank=True)
    phone_number_lookup = models.CharField(max_length=64, blank=True, db_index=True, editable=False)
    address_line = models.CharField(max_length=255, blank=True)
    village = models.CharField(max_length=150, blank=True)
    traditional_authority = models.CharField(max_length=150, blank=True)
    district = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=10, choices=Region.choices, blank=True)

    occupation_or_school = models.CharField(max_length=150, blank=True)
    patient_category = models.CharField(max_length=20, choices=PatientCategory.choices, default=PatientCategory.OUTPATIENT)

    consent_care = models.BooleanField(default=True)
    consent_teaching = models.BooleanField(default=False)
    consent_research = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)  # False once merged into another record

    registered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="patients_registered")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["last_name", "first_name"]),
            models.Index(fields=["patient_number"]),
        ]

    def __str__(self):
        return f"{self.patient_number} - {self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        self.national_id_lookup = hash_lookup_value(self.national_id) if self.national_id else ""
        self.phone_number_lookup = hash_lookup_value(self.phone_number) if self.phone_number else ""
        super().save(*args, **kwargs)

    @property
    def full_name(self) -> str:
        parts = [self.first_name, self.other_names, self.last_name]
        return " ".join(p for p in parts if p)


class NextOfKin(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="next_of_kin")
    name = models.CharField(max_length=200)
    relationship = models.CharField(max_length=100)
    phone_number = EncryptedCharField(max_length=32, blank=True)

    def __str__(self):
        return f"{self.name} ({self.relationship}) - NOK of {self.patient.patient_number}"


class PatientMergeRecord(models.Model):
    """Duplicate patients are never deleted - flagged inactive and merged.
    Brief §8.1.1 duplicate detection / merge workflow.
    """

    primary_patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="merged_from")
    duplicate_patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="merged_into")
    merged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    reason = models.TextField()
    merged_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.duplicate_patient.patient_number} merged into {self.primary_patient.patient_number}"


class ReferralRecord(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="referrals")
    source = models.CharField(max_length=200)  # facility/department name, free text for MVP
    destination = models.CharField(max_length=200)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.patient_number}: {self.source} → {self.destination}"


class DuplicateConfirmation(models.Model):
    """Audit record of a registrar explicitly confirming a possible-duplicate
    match is actually a different person (Engineer A spec §2 - safety-relevant,
    not optional telemetry).
    """

    new_patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="duplicate_confirmations")
    candidate_patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="+")
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    confirmed_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)
