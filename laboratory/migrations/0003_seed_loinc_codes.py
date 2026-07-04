from django.db import migrations

LOINC_CODES = {
    "Full Blood Count": "58410-2",
    "Malaria RDT": "87591-4",
    "HIV Rapid Test": "75622-1",
    "Random Blood Glucose": "2345-7",
    "Urinalysis": "24356-8",
}


def add_loinc_codes(apps, schema_editor):
    LabTest = apps.get_model("laboratory", "LabTest")
    for name, code in LOINC_CODES.items():
        LabTest.objects.filter(name=name).update(loinc_code=code)


def remove_loinc_codes(apps, schema_editor):
    LabTest = apps.get_model("laboratory", "LabTest")
    for name, code in LOINC_CODES.items():
        LabTest.objects.filter(name=name).update(loinc_code="")


class Migration(migrations.Migration):
    dependencies = [
        ("laboratory", "0002_seed_lab_tests"),
    ]

    operations = [migrations.RunPython(add_loinc_codes, remove_loinc_codes)]
