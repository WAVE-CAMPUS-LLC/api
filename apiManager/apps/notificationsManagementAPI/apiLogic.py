from typing import Optional
from channels.db import database_sync_to_async
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
)
from apiManager.notifications.websocket import manager
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
import bleach
import uuid
import logging
from apiManager.dependencies import get_current_user
from apiManager.utilities.notify_by_bot import notify_by_bot
from apiManager.utilities.device_info import get_device_info
from authenticationApp.models import CustomUser
from typing import List
from notificationManagement.models import Notification
from apiManager.utilities.socialFeed.feed import get_friendship_feed_from_graph
from django.utils import timezone
from authenticationApp.models import UserPushToken


router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/feed", response_model=List[dict])
async def get_feed(
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint getting the feed for a user
    """
    print(f"[get_feed API] Function called with user_id: {user_id}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_notification_feed(user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            notifications = Notification.objects.filter(
                recipient=user, type="friend_connected", is_deleted=False
            ).order_by("-created_at")[:50]

            return [
                {
                    "type": "notification",
                    "content": n.content,
                    "actor": n.actor.username if n.actor else None,
                    "timestamp": n.created_at,
                    "metadata": n.metadata,
                }
                for n in notifications
            ]
        except CustomUser.DoesNotExist:
            return []
        except Exception as e:
            logger.error(f"Error getting notification feed for user {user_id}: {e}")
            return []

    try:
        # Pull notification-based feed
        notification_feed = await get_notification_feed(user_id)

        # Pull Neo4j graph feed with error handling
        try:
            graph_feed = get_friendship_feed_from_graph(user_id)
        except Exception as graph_error:
            logger.error(f"Error getting graph feed for user {user_id}: {graph_error}")
            graph_feed = []

        # Only process graph feed if we have entries
        if graph_feed:
            # Optionally: resolve usernames for graph entries
            try:
                user_map = {
                    u.user_id: u.username
                    for u in CustomUser.objects.filter(
                        user_id__in=[entry["friend_id"] for entry in graph_feed]
                        + [entry["new_friend_id"] for entry in graph_feed]
                    )
                }
            except Exception as user_map_error:
                logger.error(f"Error creating user map: {user_map_error}")
                user_map = {}

            formatted_graph_feed = [
                {
                    "type": "graph_friendship",
                    "content": f"{user_map.get(entry['friend_id'], 'Your friend')} is now friends with {user_map.get(entry['new_friend_id'], 'someone new')}",
                    "actor": user_map.get(entry["friend_id"]),
                    "timestamp": None,  # You could add a `created_at` relationship property later
                    "metadata": entry,
                }
                for entry in graph_feed
            ]
        else:
            formatted_graph_feed = []

        # Merge and sort (if timestamps available)
        merged_feed = notification_feed + formatted_graph_feed
        return sorted(
            merged_feed,
            key=lambda x: x.get("timestamp") or timezone.now(),
            reverse=True,
        )

    except Exception as e:
        await notify_by_bot(
            f"**[API: get_feed]** \n\n Error getting feed: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=500, detail="Error getting feed")


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: int,
    current_user: CustomUser = Depends(get_current_user),
):
    await manager.connect(user_id, websocket)

    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id)


@router.post("/push/token")
async def update_push_token(
    user_id: int,
    token: str,
    current_user: CustomUser = Depends(get_current_user),
):
    try:
        user_push_token, created = UserPushToken.objects.get_or_create(
            user_id=user_id, defaults={"token": token}
        )
        logger.info(f"Push token updated successfully for user {user_id}")
        return {"status": "success", "message": "Push token updated successfully"}
    except Exception as e:
        logger.error(f"Error updating push token: {e}")
        raise HTTPException(status_code=500, detail="Error updating push token")
