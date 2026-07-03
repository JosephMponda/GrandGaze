from django.apps import AppConfig


class LaboratoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "laboratory"

    def ready(self):
        from accounts.dashboard_widgets import register_widget

        register_widget(
            title="Laboratory workload",
            url_name="laboratory:workload",
            roles=["LabTech", "Clinician", "Admin"],
            icon="flask",
        )

