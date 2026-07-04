from django.apps import AppConfig


class EmergencyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "emergency"

    def ready(self):
        from accounts.dashboard_widgets import register_widget

        register_widget(
            title="Triage Queue",
            url_name="emergency:queue",
            roles=["Nurse", "Clinician", "Admin"],
            icon="activity",
        )
