from django.apps import AppConfig


class AccountmanagementappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accountManagementApp"
    verbose_name = "Profile Management"
    
    
    def ready(self):
        from accountManagementApp import signals