from django.db import migrations


def seed_modalities(apps, schema_editor):
    ImagingModality = apps.get_model("imaging", "ImagingModality")
    modalities = [
        ("X-ray", True, True),
        ("Ultrasound", False, True),
        ("CT", True, False),
        ("MRI", True, False),
        ("Echocardiography", False, False),
    ]
    for name, pregnancy_check, supported in modalities:
        ImagingModality.objects.get_or_create(
            name=name,
            defaults={"requires_pregnancy_check": pregnancy_check, "is_mvp_supported": supported},
        )


def unseed_modalities(apps, schema_editor):
    ImagingModality = apps.get_model("imaging", "ImagingModality")
    ImagingModality.objects.filter(name__in=["X-ray", "Ultrasound", "CT", "MRI", "Echocardiography"]).delete()


class Migration(migrations.Migration):
    dependencies = [("imaging", "0001_initial")]

    operations = [migrations.RunPython(seed_modalities, unseed_modalities)]

