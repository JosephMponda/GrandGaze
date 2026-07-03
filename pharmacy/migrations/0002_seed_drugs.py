from decimal import Decimal

from django.db import migrations


def seed_drugs(apps, schema_editor):
    Drug = apps.get_model("pharmacy", "Drug")
    DrugAllergyMap = apps.get_model("pharmacy", "DrugAllergyMap")
    drugs = [
        ("Amoxicillin 250mg", "Amoxicillin", "capsule", Decimal("500"), False, False, ["penicillin"]),
        ("Ceftriaxone 1g", "Ceftriaxone", "injection", None, False, False, ["cephalosporin"]),
        ("Paracetamol 500mg", "Paracetamol", "tablet", Decimal("500"), False, False, []),
        ("Ibuprofen 200mg", "Ibuprofen", "tablet", Decimal("200"), True, True, ["nsaid"]),
        ("ORS sachet", "Oral rehydration salts", "sachet", None, False, False, []),
        ("Artemether Lumefantrine", "Artemether Lumefantrine", "tablet", None, False, False, []),
        ("Metformin 500mg", "Metformin", "tablet", None, False, True, []),
        ("Ferrous Sulphate", "Ferrous Sulphate", "tablet", None, False, False, []),
        ("Salbutamol inhaler", "Salbutamol", "inhaler", None, False, False, []),
        ("Gentamicin", "Gentamicin", "injection", None, False, True, []),
    ]
    for name, generic, formulation, pediatric_max, pregnancy, renal, keywords in drugs:
        drug, _ = Drug.objects.get_or_create(
            name=name,
            defaults={
                "generic_name": generic,
                "formulation": formulation,
                "pediatric_max_dose_mg": pediatric_max,
                "contraindicated_in_pregnancy": pregnancy,
                "contraindicated_in_renal": renal,
            },
        )
        for keyword in keywords:
            DrugAllergyMap.objects.get_or_create(drug=drug, allergen_keyword=keyword)


def unseed_drugs(apps, schema_editor):
    Drug = apps.get_model("pharmacy", "Drug")
    Drug.objects.filter(
        name__in=[
            "Amoxicillin 250mg",
            "Ceftriaxone 1g",
            "Paracetamol 500mg",
            "Ibuprofen 200mg",
            "ORS sachet",
            "Artemether Lumefantrine",
            "Metformin 500mg",
            "Ferrous Sulphate",
            "Salbutamol inhaler",
            "Gentamicin",
        ]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("pharmacy", "0001_initial")]

    operations = [migrations.RunPython(seed_drugs, unseed_drugs)]

