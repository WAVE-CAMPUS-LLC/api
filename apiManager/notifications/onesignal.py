import os
import requests
from authenticationApp.models import UserPushToken
import logging

logger = logging.getLogger(__name__)


ONESIGNAL_APP_ID = os.getenv("ONESIGNAL_APP_ID")
ONESIGNAL_API_KEY = os.getenv("ONESIGNAL_API_KEY")


def send_push_notification(user_id: str, message: str):
    try:
        token_obj = UserPushToken.objects.get(user_id=user_id)
        onesignal_token = token_obj.token

        payload = {
            "app_id": ONESIGNAL_APP_ID,
            "include_player_ids": [onesignal_token],
            "headings": {"en": "New Notification"},
            "contents": {"en": message},
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Key {ONESIGNAL_API_KEY}",
        }

        response = requests.post(
            "https://api.onesignal.com/notifications", json=payload, headers=headers
        )
        response.raise_for_status()

    except Exception as e:
        print(f"Error sending push notification: {e}")
        logger.error(f"Error sending push notification: {e}")
        return False

    return True
