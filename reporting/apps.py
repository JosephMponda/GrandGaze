from django.apps import AppConfig


class ReportingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reporting'

    def ready(self):
        from accounts.dashboard_widgets import register_widget
        register_widget(
            title="Analytics Dashboard",
            url_name="reporting:analytics_dashboard",
            roles=["Admin", "ICT", "Clinician", "Nurse"],
            icon="chart",
        )
