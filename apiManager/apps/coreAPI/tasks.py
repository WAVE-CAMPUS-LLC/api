from celery import shared_task
from django.utils import timezone
import asyncio
from authenticationApp.models import CustomUser
from accountManagementApp.models import MoodEntry
from apiManager.notifications.notification import send_notification


@shared_task
def send_daily_mood_prompts():
    """
    Task to send daily mood prompts to all users.
    This runs every day at 8 AM.
    """
    users = CustomUser.objects.all()

    for user in users:
        has_filled_today = user.mood_entries.filter(date=timezone.now().date()).exists()  # type: ignore
        if not has_filled_today:
            message = "Tell us how you're feeling! Let's see what the move is!"
            title = "What's the move today?!"
            navigate_to = "mood_entry"
            params = {"date": timezone.now().date().isoformat()}

            # Send notification to the user
            asyncio.run(
                send_notification(
                    user.user_id,
                    message,
                    title=title,
                    navigate_to=navigate_to,
                    params=params,
                )
            )
