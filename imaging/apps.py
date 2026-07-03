from django.apps import AppConfig


class ImagingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "imaging"

    def ready(self):
        from accounts.dashboard_widgets import register_widget

        register_widget(
            title="Imaging requests",
            url_name="imaging:worklist",
            roles=["Radiographer", "Clinician", "Admin"],
            icon="image",
        )

