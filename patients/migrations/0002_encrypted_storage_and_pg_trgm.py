import core.encrypted_fields
from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("patients", "0001_initial"),
    ]

    operations = [
        TrigramExtension(),
        migrations.CreateModel(
            name="PatientNumberSequence",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("prefix", models.CharField(max_length=12, unique=True)),
                ("next_value", models.PositiveIntegerField(default=1)),
            ],
        ),
        migrations.AlterField(
            model_name="historicalpatient",
            name="address_line",
            field=core.encrypted_fields.EncryptedCharField(blank=True, max_length=1024),
        ),
        migrations.AlterField(
            model_name="historicalpatient",
            name="national_id",
            field=core.encrypted_fields.EncryptedCharField(blank=True, max_length=1024),
        ),
        migrations.AlterField(
            model_name="historicalpatient",
            name="phone_number",
            field=core.encrypted_fields.EncryptedCharField(blank=True, max_length=1024),
        ),
        migrations.AlterField(
            model_name="nextofkin",
            name="phone_number",
            field=core.encrypted_fields.EncryptedCharField(blank=True, max_length=1024),
        ),
        migrations.AlterField(
            model_name="patient",
            name="address_line",
            field=core.encrypted_fields.EncryptedCharField(blank=True, max_length=1024),
        ),
        migrations.AlterField(
            model_name="patient",
            name="national_id",
            field=core.encrypted_fields.EncryptedCharField(blank=True, max_length=1024),
        ),
        migrations.AlterField(
            model_name="patient",
            name="phone_number",
            field=core.encrypted_fields.EncryptedCharField(blank=True, max_length=1024),
        ),
    ]
