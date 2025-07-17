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
        # Log the notification data being sent
        logger.info(
            "Sending notification - user_id: %s, message: %s, title: %s, navigate_to: %s, params: %s",
            user_id,
            message,
            title,
            navigate_to,
            params,
        )

        # Also print to terminal for immediate visibility
        print(
            f"[NOTIFICATION] Sending notification - user_id: {user_id}, message: {message}, title: {title}, navigate_to: {navigate_to}, params: {params}"
        )

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

        # Log the final payload being sent
        logger.info("Notification payload: %s", payload)

        # Also print payload to terminal
        print(f"[NOTIFICATION] Payload: {payload}")

        user_id_str = str(user_id)
        if user_id_str in manager.active_connections:
            logger.info("Sending via websocket to user: %s", user_id_str)
            print(f"[NOTIFICATION] Sending via websocket to user: {user_id_str}")
            await manager.send_personal_message(payload, user_id_str)
        else:
            logger.info("Sending via push notification to user: %s", user_id_str)
            print(
                f"[NOTIFICATION] Sending via push notification to user: {user_id_str}"
            )
            await send_push_notification(user_id, message, title, data=payload)

    except Exception as e:
        print(f"Error sending notification: {e}")
        logger.error("Error sending notification: %s", e)
