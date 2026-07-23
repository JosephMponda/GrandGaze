from django.conf import settings
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from core.encrypted_fields import EncryptedCharField


class Role(models.TextChoices):
    NURSE = "NURSE", "Nurse"
    CLINICIAN = "CLINICIAN", "Clinician"
    PHARMACIST = "PHARMACIST", "Pharmacist"
    LAB_TECH = "LAB_TECH", "Lab Technician"
    RADIOGRAPHER = "RADIOGRAPHER", "Radiographer"
    BILLING_OFFICER = "BILLING_OFFICER", "Billing Officer"
    ADMIN = "ADMIN", "Admin"
    ICT = "ICT", "ICT"


ROLE_GROUP_NAMES = {
    Role.NURSE: "Nurse",
    Role.CLINICIAN: "Clinician",
    Role.PHARMACIST: "Pharmacist",
    Role.LAB_TECH: "LabTech",
    Role.RADIOGRAPHER: "Radiographer",
    Role.BILLING_OFFICER: "BillingOfficer",
    Role.ADMIN: "Admin",
    Role.ICT: "ICT",
}


def group_name_for_role(role: str) -> str:
    return ROLE_GROUP_NAMES[role]


def assign_user_role_group(user, role: str) -> None:
    """Keep Profile.role and Django Group membership in sync for RBAC."""
    from django.contrib.auth.models import Group

    group, _ = Group.objects.get_or_create(name=group_name_for_role(role))
    user.groups.add(group)


class Gender(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"
    OTHER = "other", "Other"


class Profile(models.Model):
    """One-to-one extension of Django's built-in User. Do not replace User."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=32, choices=Role.choices)
    department = models.CharField(max_length=100, blank=True)
    phone_number = EncryptedCharField(max_length=32, blank=True)
    is_active_staff = models.BooleanField(default=True)
    photo = models.ImageField(upload_to="staff_photos/", blank=True)
    qualifications = models.TextField(blank=True)
    bio = models.TextField(blank=True)
    specialty = models.CharField(max_length=100, blank=True)
    employee_id = models.CharField(max_length=50, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    emergency_contact = EncryptedCharField(max_length=32, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"


class TaskPriority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    URGENT = "urgent", "Urgent"


class TaskStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class Task(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assigned_tasks")
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="tasks_assigned")
    patient = models.ForeignKey("patients.Patient", on_delete=models.SET_NULL, null=True, blank=True, related_name="tasks")
    priority = models.CharField(max_length=10, choices=TaskPriority.choices, default=TaskPriority.MEDIUM)
    status = models.CharField(max_length=12, choices=TaskStatus.choices, default=TaskStatus.PENDING)
    due_date = models.DateField(default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-priority", "due_date"]

    def __str__(self):
        return self.title
