from django.apps import AppConfig


class PharmacyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pharmacy"

    def ready(self):
        from accounts.dashboard_widgets import register_widget

        register_widget(
            title="Pharmacy queue",
            url_name="pharmacy:queue",
            roles=["Pharmacist", "Clinician", "Admin"],
            icon="pill",
        )

