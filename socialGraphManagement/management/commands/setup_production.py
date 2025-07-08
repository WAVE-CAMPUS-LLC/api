from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Setup production environment with proper migration order"

    def handle(self, *args, **kwargs):
        self.stdout.write("🚀 Setting up production environment...")
        
        try:
            # Step 1: Apply all Django schema migrations
            self.stdout.write("📋 Step 1: Applying Django schema migrations...")
            call_command("migrate", verbosity=1, interactive=False)
            
            # Step 2: Verify schema
            self.stdout.write("🔍 Step 2: Verifying database schema...")
            if not self._verify_database_schema():
                self.stdout.write(
                    self.style.ERROR("❌ Database schema verification failed. Check migrations.")
                )
                return
            
            # Step 3: Run data migrations
            self.stdout.write("📦 Step 3: Running data migrations...")
            
            self.stdout.write("  Migrating friends to graph...")
            call_command("migrate_friends_to_graph")
            
            self.stdout.write("  Migrating preferences...")
            call_command("migrate_preferences")
            
            self.stdout.write("  Migrating colleges...")
            call_command("migrate_colleges")
            
            self.stdout.write("  Migrating event relations...")
            call_command("migrate_events_relations")
            
            self.stdout.write(
                self.style.SUCCESS("✅ Production setup completed successfully!")
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error during production setup: {e}")
            )
            logger.error("Error during production setup: %s", e)
    
    def _verify_database_schema(self):
        """Verify that the required database schema exists"""
        try:
            from accountManagementApp.models import UserPreferences
            from django.db import models
            
            # Check if the preferred_times field exists in the model
            try:
                field = UserPreferences._meta.get_field('preferred_times')
                self.stdout.write("  ✅ preferred_times field verified")
                return True
            except models.FieldDoesNotExist:
                self.stdout.write(
                    self.style.WARNING("  ⚠️  Field 'preferred_times' not found in UserPreferences model")
                )
                return False
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"  ❌ Error verifying schema: {e}")
            )
            return False 