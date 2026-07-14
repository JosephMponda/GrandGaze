from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("syncapi", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="syncsubmission",
            name="result_json",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
