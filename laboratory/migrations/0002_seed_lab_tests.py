from decimal import Decimal

from django.db import migrations


def seed_lab_tests(apps, schema_editor):
    LabTest = apps.get_model("laboratory", "LabTest")
    tests = [
        ("Full Blood Count", "", "blood", None, None, "", False),
        ("Malaria RDT", "", "blood", None, None, "", False),
        ("HIV Rapid Test", "", "blood", None, None, "", False),
        ("Creatinine", "2160-0", "blood", Decimal("40"), Decimal("120"), "umol/L", True),
        ("Random Blood Glucose", "2339-0", "blood", Decimal("3.9"), Decimal("11.1"), "mmol/L", True),
        ("Urinalysis", "", "urine", None, None, "", False),
        ("Pregnancy Test", "", "urine", None, None, "", False),
    ]
    for name, loinc, specimen, low, high, unit, critical in tests:
        LabTest.objects.get_or_create(
            name=name,
            defaults={
                "loinc_code": loinc,
                "specimen_type": specimen,
                "normal_range_low": low,
                "normal_range_high": high,
                "unit": unit,
                "is_critical_if_outside_range": critical,
            },
        )


def unseed_lab_tests(apps, schema_editor):
    LabTest = apps.get_model("laboratory", "LabTest")
    LabTest.objects.filter(name__in=["Full Blood Count", "Malaria RDT", "HIV Rapid Test", "Creatinine", "Random Blood Glucose", "Urinalysis", "Pregnancy Test"]).delete()


class Migration(migrations.Migration):
    dependencies = [("laboratory", "0001_initial")]

    operations = [migrations.RunPython(seed_lab_tests, unseed_lab_tests)]

