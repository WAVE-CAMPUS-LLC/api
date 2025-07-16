import requests
from notificationManagement.models import UserPushyTokeny
import logging
import uuid

logger = logging.getLogger(__name__)

EXPO_API_URL = "https://exp.host/--/api/v2/push/send"


def send_push_notification(user_id: uuid.UUID, message: str, title: str = "WAVE."):
    try:
        token_obj = UserPushyTokeny.objects.get(user_id=user_id)
        expo_token = token_obj.token

        payload = {
            "to": expo_token,
            "sound": "default",
            "title": title,
            "body": message,
            "data": {"message": message},
        }

        headers = {
            "Content-Type": "application/json",
        }

        response = requests.post(EXPO_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        logger.info("Push notification sent successfully to user %s", user_id)
        return True
    except Exception as e:
        logger.error("Error sending push notification: %s", e)
        return False
