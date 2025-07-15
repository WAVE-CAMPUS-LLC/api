from notificationManagement.models import PushNotification
from .websocket import manager
from .onesignal import send_push_notification
import logging

logger = logging.getLogger(__name__)


async def send_notification(user_id: str, message: str):
    try:
        PushNotification.objects.create(user_id=user_id, message=message)
        await manager.send_personal_message(message, user_id)

        if user_id not in manager.active_connections:
            send_push_notification(user_id, message)

    except Exception as e:
        print(f"Error sending notification: {e}")
        logger.error(f"Error sending notification: {e}")
