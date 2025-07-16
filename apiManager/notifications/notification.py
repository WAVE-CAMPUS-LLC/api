from notificationManagement.models import PushNotification
from .websocket import manager
from .expo_notifications import send_push_notification
import logging
import uuid

logger = logging.getLogger(__name__)


async def send_notification(user_id: uuid.UUID, message: str, title: str = "WAVE."):
    try:
        PushNotification.objects.create(user_id=user_id, message=message)

        if user_id in manager.active_connections:
            await manager.send_personal_message(message, user_id)
        else:
            send_push_notification(user_id, message, title)

    except Exception as e:
        print(f"Error sending notification: {e}")
        logger.error(f"Error sending notification: {e}")
