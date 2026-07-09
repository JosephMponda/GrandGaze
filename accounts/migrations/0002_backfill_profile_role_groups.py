from django.db import migrations


ROLE_GROUP_NAMES = {
    "NURSE": "Nurse",
    "CLINICIAN": "Clinician",
    "PHARMACIST": "Pharmacist",
    "LAB_TECH": "LabTech",
    "RADIOGRAPHER": "Radiographer",
    "BILLING_OFFICER": "BillingOfficer",
    "ADMIN": "Admin",
    "ICT": "ICT",
}


def backfill_profile_role_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Profile = apps.get_model("accounts", "Profile")

    groups = {
        role: Group.objects.get_or_create(name=group_name)[0]
        for role, group_name in ROLE_GROUP_NAMES.items()
    }
    through = Group.user_set.through

    memberships = []
    for profile in Profile.objects.select_related("user"):
        group = groups.get(profile.role)
        if group:
            memberships.append(through(user_id=profile.user_id, group_id=group.pk))

    through.objects.bulk_create(memberships, ignore_conflicts=True)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(backfill_profile_role_groups, noop_reverse),
    ]
