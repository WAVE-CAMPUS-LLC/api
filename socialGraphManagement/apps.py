from django.apps import AppConfig
import sys
import logging

logger = logging.getLogger(__name__)


class SocialgraphmanagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "socialGraphManagement"

    def ready(self):
        import socialGraphManagement.signals

        if any(
            arg in sys.argv
            for arg in ["makemigrations", "migrate", "collectstatic", "shell", "test"]
        ):
            return

        try:
            from django.core.management import call_command

            call_command("migrate_friends_to_graph")

        except Exception as e:
            logger.error("Error migrating friends to graph: %s", e)
