from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class SocialgraphmanagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "socialGraphManagement"

    def ready(self):
        import socialGraphManagement.signals

        try:
            from django.core.management import call_command

            call_command("migrate_friends_to_graph")
            call_command("migrate_preferences")

        except Exception as e:
            logger.error("Error migrating friends to graph: %s", e)
