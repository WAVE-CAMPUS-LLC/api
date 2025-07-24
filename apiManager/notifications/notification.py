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
            try:
                user = CustomUser.objects.get(user_id=user_uuid)
                return PushNotification.objects.create(  # type: ignore[attr-defined]
                    user=user,
                    message=message_text,
                    title=title,
                    navigate_to=navigate_to,
                    params=params,
                )
            except CustomUser.DoesNotExist:
                logger.error(
                    "Cannot create push notification - User with user_id %s does not exist",
                    user_uuid,
                )
                return None
            except Exception as e:
                logger.error("Error creating push notification record: %s", e)
                return None

        notification_record = await create_push_notification(
            user_id, message, title, navigate_to, params
        )

        if notification_record is None:
            logger.error("Failed to create notification record for user %s", user_id)
            return False

        payload: dict[str, Any] = {
            "type": "notification",
            "title": title,
            "message": message,
        }

        # Add recipient's profile photo to the payload
        @database_sync_to_async
        def get_profile_photo_url(user_uuid):
            try:
                user = CustomUser.objects.get(user_id=user_uuid)
                profile = getattr(user, "user_profile", None)
                if profile and profile.profile_photo:
                    return profile.profile_photo.url
            except Exception:
                pass
            return None

        recipient_profile_photo = await get_profile_photo_url(user_id)
        if params is None:
            params = {}
        params = dict(params)  # ensure mutable
        params["profile_photo"] = recipient_profile_photo

        # If params contains a sender_username or username, try to add sender's profile photo
        sender_username = params.get("sender_username") or params.get("username")
        if sender_username:

            @database_sync_to_async
            def get_sender_profile_photo_url(sender_username):
                try:
                    user = CustomUser.objects.get(username=sender_username)
                    profile = getattr(user, "user_profile", None)
                    if profile and profile.profile_photo:
                        return profile.profile_photo.url
                except Exception:
                    pass
                return None

            sender_profile_photo = await get_sender_profile_photo_url(sender_username)
            params["sender_profile_photo"] = sender_profile_photo

        if navigate_to:
            payload["navigate_to"] = navigate_to

        if params:
            payload["params"] = params

        # Log the final payload being sent
        logger.info("Notification payload: %s", payload)

        # Also print payload to terminal
        print(f"[NOTIFICATION] Payload: {payload}")

        user_id_str = str(user_id)
        notification_sent = False

        # Try websocket first
        if user_id_str in manager.active_connections:
            try:
                logger.info("Sending via websocket to user: %s", user_id_str)
                print(f"[NOTIFICATION] Sending via websocket to user: {user_id_str}")
                await manager.send_personal_message(payload, user_id_str)
                notification_sent = True
                logger.info(
                    "Websocket notification sent successfully to user: %s", user_id_str
                )
            except Exception as ws_error:
                logger.error(
                    "Failed to send websocket notification to user %s: %s",
                    user_id_str,
                    ws_error,
                )
                # Continue to try push notification as fallback

        # If websocket failed or user not connected, try push notification
        if not notification_sent:
            logger.info("Sending via push notification to user: %s", user_id_str)
            print(
                f"[NOTIFICATION] Sending via push notification to user: {user_id_str}"
            )

            push_success = await send_push_notification(
                user_id, message, title, data=payload
            )
            if push_success:
                notification_sent = True
                logger.info(
                    "Push notification sent successfully to user: %s", user_id_str
                )
            else:
                logger.warning("Push notification failed for user: %s", user_id_str)

        if not notification_sent:
            logger.warning("All notification methods failed for user: %s", user_id_str)
            return False

        return True

    except Exception as e:
        print(f"Error sending notification: {e}")
        logger.error("Error sending notification to user %s: %s", user_id, e)
        return False
