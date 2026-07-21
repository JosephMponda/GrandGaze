from django.apps import AppConfig


class DialysisConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dialysis"

    def ready(self):
        from accounts.dashboard_widgets import register_widget

        register_widget(
            title="Dialysis Sessions Today",
            url_name="dialysis:dashboard",
            roles=["Clinician", "Nurse", "Admin"],
            icon="dialysis",
        )