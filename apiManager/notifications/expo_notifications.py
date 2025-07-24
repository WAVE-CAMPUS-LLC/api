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
            try:
                user = CustomUser.objects.get(user_id=user_uuid)
                return UserPushyTokeny.objects.get(user=user)
            except CustomUser.DoesNotExist:
                logger.warning("User with user_id %s does not exist", user_uuid)
                return None
            except UserPushyTokeny.DoesNotExist:
                logger.info(
                    "No push token found for user %s - user may not have registered for push notifications",
                    user_uuid,
                )
                return None

        token_obj = await get_push_token(user_id)

        # If no push token is found, log and return gracefully
        if token_obj is None:
            logger.info(
                "Skipping push notification for user %s - no push token registered",
                user_id,
            )
            return False

        expo_token = token_obj.token

        # Validate that we have a valid expo token
        if not expo_token or not expo_token.strip():
            logger.warning("Empty or invalid push token for user %s", user_id)
            return False

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
        response_data = response.json()
        print(response_data)

        response.raise_for_status()

        # Check for Expo-specific errors in the response
        if isinstance(response_data, dict) and "data" in response_data:
            expo_errors = response_data.get("data", {}).get("errors", [])
            if expo_errors:
                logger.warning(
                    "Expo push notification errors for user %s: %s",
                    user_id,
                    expo_errors,
                )
                return False

        logger.info("Push notification sent successfully to user %s", user_id)
        return True

    except requests.exceptions.RequestException as e:
        logger.error(
            "Network error sending push notification to user %s: %s", user_id, e
        )
        return False
    except Exception as e:
        logger.error("Error sending push notification to user %s: %s", user_id, e)
        return False
