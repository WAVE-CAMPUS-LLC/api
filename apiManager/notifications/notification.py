from notificationManagement.models import PushNotification
from .websocket import manager
from .expo_notifications import send_push_notification
import logging
import uuid
from channels.db import database_sync_to_async
from authenticationApp.models import CustomUser
from typing import Any, Optional

logger = logging.getLogger(__name__)


async def send_notification(
    user_id: uuid.UUID,
    message: str,
    title: str = "WAVE.",
    navigate_to: Optional[str] = None,
    params: Optional[dict] = None,
):
    try:
        # Get user by UUID and use their primary key ID for PushNotification
        @database_sync_to_async
        def create_push_notification(
            user_uuid, message_text, title, navigate_to, params
        ):
            user = CustomUser.objects.get(user_id=user_uuid)
            return PushNotification.objects.create(  # type: ignore[attr-defined]
                user=user,
                message=message_text,
                title=title,
                navigate_to=navigate_to,
                params=params,
            )

        await create_push_notification(user_id, message, title, navigate_to, params)

        payload: dict[str, Any] = {
            "type": "notification",
            "title": title,
            "message": message,
        }

        if navigate_to:
            payload["navigate_to"] = navigate_to

        if params:
            payload["params"] = params

        user_id_str = str(user_id)
        if user_id_str in manager.active_connections:
            await manager.send_personal_message(payload, user_id_str)
        else:
            await send_push_notification(user_id, message, title, data=payload)

    except Exception as e:
        print(f"Error sending notification: {e}")
        logger.error("Error sending notification: %s", e)
