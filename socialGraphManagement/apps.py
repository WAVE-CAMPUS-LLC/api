from django.apps import AppConfig
import logging
from threading import Thread
from django.db import connection
from django.core.management import call_command
import os

logger = logging.getLogger(__name__)


class SocialgraphmanagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "socialGraphManagement"

    def ready(self):
        import socialGraphManagement.signals

        # Check if we're in production environment
        ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
        if ENVIRONMENT != "production":
            logger.info("Not in production environment. Skipping data migrations.")
            return

        # Schema verification function
        def verify_schema():
            """Verify that the required database schema exists"""
            try:
                from accountManagementApp.models import UserPreferences
                from django.db import models

                # Check if the preferred_times field exists in the model
                try:
                    field = UserPreferences._meta.get_field("preferred_times")
                    logger.info(
                        "Database schema verification passed - preferred_times field found"
                    )
                    return True
                except models.FieldDoesNotExist:
                    logger.warning(
                        "Field 'preferred_times' not found in UserPreferences model. Schema migration needed."
                    )
                    return False

            except Exception as e:
                logger.error("Error verifying database schema: %s", e)
                return False

        # Run migration commands in a separate thread to avoid async context issues
        def run_migrations():
            try:
                # First ensure all Django migrations are applied
                logger.info("Checking database migrations...")
                call_command("migrate", verbosity=0, interactive=False)

                # Verify the required table structure exists before running data migrations
                if not verify_schema():
                    logger.warning(
                        "Database schema not ready for data migrations. Skipping..."
                    )
                    return

                logger.info("Starting data migrations...")
                call_command("migrate_friends_to_graph")
                call_command("migrate_preferences")
                call_command("migrate_colleges")
                call_command("migrate_events_relations")
                call_command("migrate_crews_to_graph")
                logger.info("Data migrations completed successfully")

            except Exception as e:
                logger.error("Error during migration process: %s", e)

        # Execute migrations in a background thread to avoid blocking async context
        migration_thread = Thread(target=run_migrations, daemon=True)
        migration_thread.start()
