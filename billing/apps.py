from django.apps import AppConfig


class BillingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'billing'

    def ready(self):
        from accounts.dashboard_widgets import register_widget
        register_widget(
            title="Billing Dashboard",
            url_name="billing:dashboard",
            roles=["BillingOfficer", "Admin"],
            icon="bill",
        )
