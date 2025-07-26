from celery import shared_task
from django.utils import timezone
import asyncio
import logging
from authenticationApp.models import CustomUser
from accountManagementApp.models import MoodEntry
from apiManager.notifications.notification import send_notification

logger = logging.getLogger(__name__)


@shared_task
def send_daily_mood_prompts():
    """
    Task to send daily mood prompts to all users.
    This runs every day at 7:40 PM EST.
    """
    logger.info("Starting daily mood prompts task")

    users = CustomUser.objects.all()
    logger.info(f"Found {users.count()} users to check")

    notifications_sent = 0
    notifications_failed = 0

    for user in users:
        logger.info(f"Checking user: {user.username}")

        has_filled_today = user.mood_entries.filter(date=timezone.now().date()).exists()  # type: ignore
        logger.info(f"User {user.username} has filled mood today: {has_filled_today}")

        if not has_filled_today:
            message = "Tell us how you're feeling! Let's see what the move is!"
            title = "What's the move today?!"
            navigate_to = "mood_entry"
            params = {"date": timezone.now().date().isoformat()}

            logger.info(f"Sending notification to user: {user.username}")

            try:
                # Send notification to the user
                result = asyncio.run(
                    send_notification(
                        user.user_id,
                        message,
                        title=title,
                        navigate_to=navigate_to,
                        params=params,
                    )
                )

                if result:
                    logger.info(f"✅ Notification sent successfully to {user.username}")
                    notifications_sent += 1
                else:
                    logger.error(f"❌ Failed to send notification to {user.username}")
                    notifications_failed += 1

            except Exception as e:
                logger.error(
                    f"❌ Error sending notification to {user.username}: {str(e)}"
                )
                notifications_failed += 1
        else:
            logger.info(f"Skipping {user.username} - already filled mood today")

    logger.info(
        f"Task completed. Notifications sent: {notifications_sent}, Failed: {notifications_failed}"
    )
