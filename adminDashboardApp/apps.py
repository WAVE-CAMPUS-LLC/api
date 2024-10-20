from django.apps import AppConfig


class AdmindashboardappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "adminDashboardApp"
    
    def ready(self):
        import adminDashboardApp.signals  # Register signals
