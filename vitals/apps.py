from django.apps import AppConfig


class VitalsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'vitals'

    def ready(self):
        from accounts.dashboard_widgets import register_widget

        register_widget(
            title="Patients with abnormal vitals (last 4h)",
            url_name="reporting:recent_alerts",
            roles=["Nurse", "Clinician", "Admin"],
            icon="vital-signs",
        )
