from django.apps import AppConfig


class SocialappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "socialApp"

    def ready(self):
        import socialApp.signals  # Import signals when the app is ready
        import os
        from django.core.management import call_command
        import logging

        logger = logging.getLogger(__name__)

        try:
            logger.info("Running generate_all_crew_images command on app ready...")
            # call_command("generate_all_crew_images")  # Disabled: causes ORM async context error. Run manually instead.
        except Exception as e:
            logger.error("Error running generate_all_crew_images: %s", e)
