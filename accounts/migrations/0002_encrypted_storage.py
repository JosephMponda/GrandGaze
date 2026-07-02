import core.encrypted_fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="historicalprofile",
            name="phone_number",
            field=core.encrypted_fields.EncryptedCharField(blank=True, max_length=1024),
        ),
        migrations.AlterField(
            model_name="profile",
            name="phone_number",
            field=core.encrypted_fields.EncryptedCharField(blank=True, max_length=1024),
        ),
    ]
