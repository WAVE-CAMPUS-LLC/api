from notificationManagement.models import PushNotification
from .websocket import manager
from .expo_notifications import send_push_notification
import logging
import uuid
from channels.db import database_sync_to_async
from authenticationApp.models import CustomUser

logger = logging.getLogger(__name__)


async def send_notification(user_id: uuid.UUID, message: str, title: str = "WAVE."):
    try:
        # Get user by UUID and use their primary key ID for PushNotification
        @database_sync_to_async
        def create_push_notification(user_uuid, message_text):
            user = CustomUser.objects.get(user_id=user_uuid)
            return PushNotification.objects.create(user=user, message=message_text)

        await create_push_notification(user_id, message)

        user_id_str = str(user_id)
        if user_id_str in manager.active_connections:
            await manager.send_personal_message(message, user_id_str)
        else:
            await send_push_notification(user_id, message, title)

    except Exception as e:
        print(f"Error sending notification: {e}")
        logger.error(f"Error sending notification: {e}")
