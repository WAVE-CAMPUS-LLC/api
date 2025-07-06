from django.apps import AppConfig


class SocialgraphmanagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "socialGraphManagement"

    def ready(self):
        import socialGraphManagement.signals
