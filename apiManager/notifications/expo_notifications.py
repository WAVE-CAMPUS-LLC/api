import requests
from notificationManagement.models import UserPushyTokeny
from authenticationApp.models import CustomUser
from channels.db import database_sync_to_async
import logging
import uuid
from typing import Optional

logger = logging.getLogger(__name__)

EXPO_API_URL = "https://exp.host/--/api/v2/push/send"


async def send_push_notification(
    user_id: uuid.UUID, message: str, title: str = "WAVE.", data: Optional[dict] = None
):
    try:
        # Use sync_to_async for ORM call
        @database_sync_to_async
        def get_push_token(user_uuid):
            user = CustomUser.objects.get(user_id=user_uuid)
            return UserPushyTokeny.objects.get(user=user)  # type: ignore[attr-defined]

        token_obj = await get_push_token(user_id)
        expo_token = token_obj.token

        payload = {
            "to": expo_token,
            "sound": "default",
            "title": title,
            "body": message,
            "data": data or {"message": message},
        }

        headers = {
            "Content-Type": "application/json",
        }

        response = requests.post(EXPO_API_URL, json=payload, headers=headers)
        print(response.json())
        response.raise_for_status()
        logger.info("Push notification sent successfully to user %s", user_id)
        return True
    except Exception as e:
        logger.error("Error sending push notification: %s", e)
        return False
