import requests
from authenticationApp.models import UserPushToken
import logging
import uuid

logger = logging.getLogger(__name__)

EXPO_API_URL = "https://exp.host/--/api/v2/push/send"


def send_push_notification(user_id: uuid.UUID, message: str, title: str = "WAVE."):
    try:
        token_obj = UserPushToken.objects.get(user_id=user_id)
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
        logger.info(f"Push notification sent successfully to user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error sending push notification: {e}")
        return False
