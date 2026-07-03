from django.apps import AppConfig


class InpatientConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "inpatient"

    def ready(self):
        from accounts.dashboard_widgets import register_widget

        register_widget(
            title="Bed Occupancy",
            url_name="inpatient:dashboard",
            roles=["Clinician", "Nurse", "Admin"],
            icon="activity",
        )