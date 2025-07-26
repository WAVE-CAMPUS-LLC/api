from django.core.management.base import BaseCommand
from apiManager.apps.coreAPI.tasks import send_daily_mood_prompts


class Command(BaseCommand):
    help = "Test the daily mood prompts task"

    def handle(self, *args, **options):
        self.stdout.write("Testing daily mood prompts task...")

        try:
            # Call the task directly
            result = send_daily_mood_prompts()
            self.stdout.write(self.style.SUCCESS("Task completed successfully!"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Task failed: {str(e)}"))
