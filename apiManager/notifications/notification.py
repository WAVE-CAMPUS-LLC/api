from notificationManagement.models import PushNotification
from .websocket import manager
from .expo_notifications import send_push_notification
import logging
import uuid
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


async def send_notification(user_id: uuid.UUID, message: str, title: str = "WAVE."):
    try:
        # Use sync_to_async for ORM
        await database_sync_to_async(PushNotification.objects.create)(
            user_id=user_id, message=message
        )

        user_id_str = str(user_id)
        if user_id_str in manager.active_connections:
            await manager.send_personal_message(message, user_id_str)
        else:
            send_push_notification(user_id, message, title)

    except Exception as e:
        print(f"Error sending notification: {e}")
        logger.error(f"Error sending notification: {e}")
