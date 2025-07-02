from django.apps import AppConfig


class AmbassadormanagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ambassadorManagement"

    def ready(self):
        import ambassadorManagement.signals
