from django.conf import settings
from django.db import models
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


class Profile(models.Model):
    """One-to-one extension of Django's built-in User. Do not replace User."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=32, choices=Role.choices)
    department = models.CharField(max_length=100, blank=True)  # free text for MVP; FK in Phase 2
    phone_number = EncryptedCharField(max_length=32, blank=True)
    is_active_staff = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"
